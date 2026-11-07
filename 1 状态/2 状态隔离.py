from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.constants import START, END


# 全局状态类
class MyState(TypedDict):
    query: str
    rag_result: str
    web_result: str
    final_answer: str


# 输入状态类（规定输入时只能输入 query）
class InputState(TypedDict):
    query: str


# 输出状态类（规定输出时只输出 final_answer）
class OutputState(TypedDict):
    final_answer: str


# 私有状态（表示中间节点的状态）
class SearchState(TypedDict):
    rag_result: str
    web_result: str


# rag节点
def rag_node(state: MyState):
    print(f"{state["query"]}: rag检索")
    return {
        "rag_result": "rag检索结果",
    }


# 网络搜索节点
def web_node(state: MyState):
    print(f"{state["query"]}: web搜索")
    return {
        "web_result": "web搜索结果",
    }


# 最终回答节点
def final_answer_node(state: MyState):
    rag_result = state["rag_result"]
    web_result = state["web_result"]
    return {
        "final_answer": rag_result + "\n" + web_result,
    }


# 创建StateGraph对象时传入全局、输入、输出状态
builder = StateGraph(state_schema=MyState, input_schema=InputState, output_schema=OutputState)

# 添加节点
builder.add_node(rag_node)
builder.add_node(web_node)
builder.add_node(final_answer_node)

# 添加边
builder.add_edge(START, "rag_node")
builder.add_edge(START, "web_node")
builder.add_edge("rag_node", "final_answer_node")
builder.add_edge("web_node", "final_answer_node")
builder.add_edge("final_answer_node", END)

# 编译得到图对象
graph = builder.compile()

# 执行图对象
output_state = graph.invoke(input={
    "query": "什么是langgraph",
})
print(output_state)
