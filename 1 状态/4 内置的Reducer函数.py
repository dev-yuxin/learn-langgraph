import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import add_messages, StateGraph, MessagesState
from langgraph.constants import START, END

load_dotenv(override=True)


# 状态定义
# class MyState(TypedDict):
#     query: str
#     # add_messages 是内置的规约函数
#     # 规则：根据 message 的 id，如果是已有id，直接替换旧message。如果是新id，尾插一条消息。
#     messages: Annotated[list[BaseMessage], add_messages]
#     answer: str


# 等价于上面的写法
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
output_state = graph.invoke({
    "query": "你好，你是谁"
})
for message in output_state["messages"]:
    message.pretty_print()
print("answer: ",output_state["answer"])
