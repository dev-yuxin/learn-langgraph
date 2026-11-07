import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, MessagesState
from langgraph.constants import START, END

load_dotenv(override=True)


# 状态定义
class MyState(MessagesState):
    query: str
    answer: str


# 输入节点
def input_node(state: MyState):
    return {
        "query": state["query"],
        "messages": [HumanMessage(content=state["query"])]
    }


# 大模型
llm = init_chat_model(
    api_key=os.getenv("bailian_api_key"),
    base_url=os.getenv("bailian_base_url"),
    model_provider="openai",
    model="qwen-flash"
)


# 大模型节点
def llm_node(state: MyState):
    ai_message = llm.invoke(input=state["messages"])
    return {
        "messages": [ai_message],
        "answer": ai_message.content
    }


# 创建 StateGraph 对象
builder = StateGraph(MyState)

# 添加节点
builder.add_node(input_node)
builder.add_node(llm_node)

# 添加边
builder.add_edge(START, "input_node")
builder.add_edge("input_node", "llm_node")
builder.add_edge("llm_node", END)

"""
短期记忆：
    当前会话中直接进入模型上下文窗口的信息，比如最近几轮对话、系统提示、工具结果。
    短期记忆依赖于会话id
    langchain和langgraph中短期记忆是指checkpointer，可以存内存里，也可以存数据库
长期记忆：
    存在模型上下文之外、跨会话持久保留、需要时检索回来的信息，比如用户偏好、历史摘要、事实档案、知识片段。
    长期记忆是跨会话的
    langchain和langgraph中长期记忆是指store，可以存内存里，也可以存数据库
"""

# 编译图（使用内存记录checkpointer）
graph = builder.compile(checkpointer=InMemorySaver())

# 设置 thread_id
config = {
    "configurable": {
        "thread_id": "thread_1"
    }
}

# 第一次运行
output_state = graph.invoke(input={
    "query": "你好，我是小明"
}, config=config)
print(output_state["answer"])

# 第二次运行（传入同样的thread_id）
# 由于有了记忆，所以 state 是上一次运行完后的 state，保留了 messages
output_state = graph.invoke(input={
    "query": "我是谁"
}, config=config)
print(output_state["answer"])

# 查看最新的检查点
print(graph.get_state(config=config))
# 查看所有检查点（新的在前，旧的在后）
history = graph.get_state_history(config=config)
for checkpoint in history:
    print(checkpoint)
