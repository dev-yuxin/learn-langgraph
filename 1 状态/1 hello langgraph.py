from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.constants import START, END


# 状态类
# 继承 TypedDict，是一个字典（推荐）
# 也可以继承 pydantic.BaseModel
# 也可以使用 @dataclass
class MyState(TypedDict):
    query: str
    rag_result: str
    web_result: str
    final_answer: str


# 创建节点，节点本质是一个函数
# 入参至少包含一个状态参数
# 返回一个表示增量更新的状态
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


# 创建StateGraph对象
builder = StateGraph(MyState)

# 添加节点（如果不指定名称则使用函数名）
builder.add_node(rag_node)
builder.add_node(web_node)
builder.add_node("final_answer", final_answer_node)

# 添加边（传入节点名称）
# START 和 END 是两个特殊节点，START必须设置，END可不设置
builder.add_edge(START, "rag_node")
builder.add_edge(START, "web_node")
builder.add_edge("rag_node", "final_answer")
builder.add_edge("web_node", "final_answer")
builder.add_edge("final_answer", END)

# 编译得到图对象
graph = builder.compile()

# 执行图对象
# input 传入初始状态
output_state = graph.invoke(input={
    "query": "什么是langgraph",
})
print(output_state)
