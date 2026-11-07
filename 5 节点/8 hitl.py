import ast
import os
from datetime import datetime

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START, END
from langgraph.graph import MessagesState, StateGraph
from langgraph.types import interrupt, Command, Interrupt

load_dotenv(override=True)

# 大模型
llm = init_chat_model(
    api_key=os.getenv("bailian_api_key"),
    base_url=os.getenv("bailian_base_url"),
    model_provider="openai",
    model="deepseek-v4.1-flash"
)


# 工具
@tool
def get_curtime():
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def get_weather(city: str, time: str):
    """
    获取指定城市时间的天气

    Args:
        city: 城市
        time: 时间
    """
    return f"{city} {time} 20°，下雨"


@tool
def send_email(receiver: str, title: str, content: str):
    """
    发送邮件

    Args:
        receiver: 收件方邮件地址
        title: 邮件标题
        content: 邮件内容
    """
    print("发送邮件成功")
    return True


# 绑定工具
tools = [get_curtime, get_weather, send_email]
tools_map = {"get_curtime": get_curtime, "get_weather": get_weather, "send_email": send_email}
llm_with_tools = llm.bind_tools(tools)


# 状态类
class MyState(MessagesState):
    query: str
    last_ai_message: AIMessage
    answer: str


# 输入节点
def input_node(state: MyState):
    human_message = HumanMessage(content=state["query"])
    return {
        "messages": [human_message]
    }


# 大模型节点
def llm_node(state: MyState):
    ai_message = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [ai_message],
        "last_ai_message": ai_message
    }


# 工具节点
def tool_node(state: MyState, config: RunnableConfig):
    last_ai_message = state["last_ai_message"]
    tool_calls = last_ai_message.tool_calls or []

    # interrupt_on 格式
    # {
    #     "tool1": True,
    #     "tool2": False,
    #     "tool3": {
    #         "allowed_decisions": ["approve", "reject", "edit", "respond"],
    #         "description": ""
    #     }
    # }
    interrupt_on = (config or {}).get("configurable", {}).get("interrupt_on", {})

    def _need_approval(tool_call) -> bool:
        tool_config = interrupt_on.get(tool_call["name"], False)
        return tool_config is True or isinstance(tool_config, dict)

    need_approval_calls = [tc for tc in tool_calls if _need_approval(tc)]

    # 注意：interrupt 恢复时本节点会从头重跑，
    # 因此所有工具的“实际执行”都必须放在 interrupt 之后，
    # 否则无需审批的工具会被执行两次
    decisions = []
    if need_approval_calls:
        action_requests = []
        review_configs = []

        for tool_call in need_approval_calls:
            name = tool_call["name"]
            args = tool_call.get("args", {}) or {}
            tool_config = interrupt_on.get(name, False)

            if isinstance(tool_config, dict):
                description = tool_config.get("description", f"工具 {name}, 参数 {args} 需要审批")
                allowed_decisions = tool_config.get(
                    "allowed_decisions", ["approve", "reject", "edit", "respond"]
                )
            else:
                # tool_config 为 True 的情况
                description = f"工具 {name}, 参数 {args} 需要审批"
                allowed_decisions = ["approve", "reject", "edit", "respond"]

            action_requests.append(
                {
                    "name": name,
                    "args": args,
                    "description": description
                }
            )
            review_configs.append(
                {
                    "action_name": name,
                    "allowed_decisions": allowed_decisions
                }
            )

        # hitl_request 格式
        # {
        #     "action_requests": [
        #         {
        #             "name": name,
        #             "args": args,
        #             "description": f"是否调用工具: {name}, 参数: {args} ?"
        #         }
        #     ],
        #     "review_configs": [
        #         {
        #             "action_name": name,
        #             "allowed_decisions": ["approve", "reject", "edit", "respond"]
        #         }
        #     ]
        # }
        hitl_request = {"action_requests": action_requests, "review_configs": review_configs}

        # hitl_response 格式
        # {
        #     "decisions": [
        #         {
        #             "type": "approve"
        #         },
        #         {
        #             "type": "edit",
        #             "edited_action": {
        #                 "args": {}
        #             }
        #         },
        #         {
        #             "type": "reject",
        #             "message": "拒绝原因"
        #         },
        #         {
        #             "type": "respond",
        #             "message": "直接替代工具返回结果"
        #         },
        #     ]
        # }
        hitl_response = interrupt(hitl_request) or {}
        decisions = hitl_response.get("decisions", []) or []

    # 将决策按 tool_call_id 映射，避免顺序/缺失导致错位
    decision_by_call_id = {
        tool_call["id"]: decision for tool_call, decision in zip(need_approval_calls, decisions)
    }

    for tool_call in tool_calls:
        name = tool_call["name"]
        args = tool_call.get("args", {}) or {}
        tool_call_id = tool_call["id"]
        tool_func = tools_map[name]

        # 不需要审批：直接执行
        if not _need_approval(tool_call):
            result = tool_func.invoke(args)
            tool_message = ToolMessage(tool_call_id=tool_call_id, content=result)

        # 需要审批
        else:
            decision = decision_by_call_id.get(tool_call_id, {"type": "reject"})
            decision_type = decision.get("type")

            if decision_type == "approve":
                result = tool_func.invoke(args)
                tool_message = ToolMessage(tool_call_id=tool_call_id, content=result)

            elif decision_type == "reject":
                tool_message = ToolMessage(tool_call_id=tool_call_id,
                                           content=decision.get("message") or "用户拒绝调用工具")
            elif decision_type == "edit":
                new_args = decision.get("edited_action", {}).get("args", {}) or {}
                result = tool_func.invoke(new_args)
                tool_message = ToolMessage(tool_call_id=tool_call_id, content=result)
            elif decision_type == "respond":
                tool_message = ToolMessage(tool_call_id=tool_call_id, content=decision.get("message") or "")
            else:
                tool_message = ToolMessage(tool_call_id=tool_call_id, content="未知的审批决策，已跳过该工具调用")

        return {"messages": [tool_message]}


# 输出节点
def output_node(state: MyState):
    last_ai_message = state["last_ai_message"]
    return {
        "answer": last_ai_message.content
    }


# 创建 StateGraph 对象
builder = StateGraph(state_schema=MyState)

# 添加节点
builder.add_node(input_node)
builder.add_node(llm_node)
builder.add_node(tool_node)
builder.add_node(output_node)

# 添加边
builder.add_edge(START, "input_node")
builder.add_edge("input_node", "llm_node")


def llm_node_router(state: MyState):
    last_ai_message = state["last_ai_message"]
    if last_ai_message.tool_calls:
        return "tool_node"
    else:
        return "output_node"


builder.add_conditional_edges("llm_node", llm_node_router)
builder.add_edge("tool_node", "llm_node")
builder.add_edge("output_node", END)

# 编译图
graph = builder.compile(checkpointer=InMemorySaver())

# 设置 config
config = {
    "configurable": {
        "thread_id": "thread_1",
        "interrupt_on": {
            "get_curtime": False,
            "get_weather": {
                "allowed_decisions": ["approve", "reject", "edit", "respond"],
                "description": "查询天气工具需要审批"
            },
            "send_email": True
        }
    }
}


# 处理中断
# 处理中断
def deal_interrupts(interrupts: list[Interrupt]):
    resume_map = {}
    for interr in interrupts:
        # hitl_request 格式
        # {
        #     "action_requests": [
        #         {
        #             "name": 'send_email',
        #             "args": {},
        #             "description": ""
        #         }
        #     ],
        #     "review_configs": [
        #         {
        #             "action_name": "send_email",
        #             "allowed_decisions": ["approve", "reject"]
        #         }
        #     ]
        # }
        hitl_request = interr.value
        # hitl_response 格式
        # {
        #     "decisions": [
        #         {
        #             "type": "approve"
        #         },
        #         {
        #             "type": "edit",
        #             "edited_action": {
        #                 "args": {}
        #             }
        #         },
        #         {
        #             "type": "reject",
        #             "message": "拒绝原因"
        #         },
        #         {
        #             "type": "respond",
        #             "message": "直接替代工具返回结果"
        #         },
        #     ]
        # }
        hitl_response = {"decisions": []}
        for action, review_cfg in zip(hitl_request.get("action_requests", []), hitl_request.get("review_configs", [])):
            print(action.get("description", "工具需要审批"))
            allowed_decisions = review_cfg.get(
                "allowed_decisions", ["approve", "reject", "edit", "respond"]
            )
            while True:
                decision_type = input(f"请输入({'/'.join(allowed_decisions)}): ").strip().lower()
                if decision_type not in allowed_decisions:
                    print("输入错误，请重新输入")
                else:
                    break

            if decision_type == "approve":
                decision = {"type": "approve"}
                hitl_response["decisions"].append(decision)
            elif decision_type == "reject":
                message = input("请输入拒绝原因（可跳过）").strip()
                decision = {"type": "reject"}
                if message:
                    decision["message"] = message
                hitl_response["decisions"].append(decision)
            elif decision_type == "edit":
                while True:
                    new_args_str = input("请输入新的参数（字典字符串格式）:")
                    try:
                        new_args = ast.literal_eval(new_args_str)
                        break
                    except Exception as e:
                        print("输入错误，请重新输入", e)
                decision = {
                    "type": "edit",
                    "edited_action": {
                        "args": new_args
                    }
                }
                hitl_response["decisions"].append(decision)
            elif decision_type == "respond":
                message = input("请输入工具结果:").strip()
                decision = {
                    "type": "respond",
                    "message": message
                }
                hitl_response["decisions"].append(decision)
            else:
                decision = {
                    "type": "respond",
                    "message": "无效审批类型，跳过工具"
                }
                hitl_response["decisions"].append(decision)
        resume_map[interr.id] = hitl_response
    return resume_map


if __name__ == '__main__':
    iterator = graph.stream(
        input={
            "query": "请帮我查询北京明天天气，然后发送邮件到test@qq.com，邮件标题是今日天气，内容是你搜索的内容，并且根据天气添加提醒"
        },
        config=config,
    )

    while True:
        interrupts = []
        # 打印消息并收集中断
        for item in iterator:
            messages = (item.get("input_node") or
                        item.get("llm_node") or
                        item.get("tool_node") or
                        item.get("output_node") or {}).get("messages", [])
            for message in messages:
                message.pretty_print()
            interrupts = item.get("__interrupt__", [])
        if not interrupts:
            break
        else:
            resume = deal_interrupts(interrupts)
            iterator = graph.stream(
                input=Command(resume=resume),
                config=config,
            )
