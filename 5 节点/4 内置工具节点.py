import os
from datetime import datetime
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.constants import START, END
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

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


# 绑定工具
tools = [get_curtime, get_weather]
llm_with_tools = llm.bind_tools(tools)


# 状态类
class MyState(MessagesState):
    query: str
    last_ai_message: AIMessage
    answer: str


# 输入节点
def input_node(state: MyState):
    humman_message = HumanMessage(content=state["query"])
    return {
        "messages": [humman_message]
    }


# 大模型节点
def llm_node(state: MyState):
    ai_message = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [ai_message],
        "last_ai_message": ai_message
    }


# 内置的工具节点
tool_node = ToolNode(tools=tools)


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
builder.add_node("tool_node", tool_node)  # tool_node 不是函数，所以必须指定节点名
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
graph = builder.compile()

# 运行
iterator = graph.stream(input={
    "query": "请帮我查询明天北京的天气"
}, stream_mode="updates")
for item in iterator:
    print(item)
