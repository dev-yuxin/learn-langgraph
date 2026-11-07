import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, MessagesState
from langgraph.constants import START, END

load_dotenv(override=True)


# 状态类
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

# 编译图
graph = builder.compile()

# 运行图
iterator = graph.stream(
    input={"query": "你好"},
    # 混合模式
    stream_mode=("values", "updates")
)
for item in iterator:
    print(item)
