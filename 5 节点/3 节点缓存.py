import os
import time

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, MessagesState
from langgraph.constants import START, END
from langgraph.cache.memory import InMemoryCache
from langgraph.types import CachePolicy

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
    print("llm_node")
    ai_message = llm.invoke(input=state["messages"])
    return {
        "messages": [ai_message],
        "answer": ai_message.content
    }


# 创建 StateGraph 对象
builder = StateGraph(MyState)

# 添加节点
builder.add_node(input_node)


def key_func(state: MyState):
    """
    进入大模型节点时输入完全一致将补运行节点，走缓存
    由于每次进入时 messages 中的 id 会不同，我们只需判断 query 是否相同
    """
    return state["query"]


# 加入缓存机制
builder.add_node(llm_node, cache_policy=CachePolicy(key_func=key_func, ttl=5))

# 添加边
builder.add_edge(START, "input_node")
builder.add_edge("input_node", "llm_node")
builder.add_edge("llm_node", END)

# 编译图（加入缓存机制，存储到内存）
graph = builder.compile(cache=InMemoryCache())

# 运行图
# 第一次运行，记录缓存
output_state = graph.invoke({
    "query": "你好，你是谁"
})
print(output_state["answer"])
print("=" * 100)
# 第二次运行，走缓存
output_state = graph.invoke({
    "query": "你好，你是谁"
})
print(output_state["answer"])
print("=" * 100)
# 第三次运行，缓存失效
time.sleep(5)
output_state = graph.invoke({
    "query": "你好，你是谁"
})
print(output_state["answer"])
