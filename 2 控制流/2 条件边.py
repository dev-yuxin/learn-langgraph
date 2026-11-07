from typing import TypedDict, Literal, Iterable
from langgraph.constants import START, END
from langgraph.graph import StateGraph


# 状态类
class MyState(TypedDict):
    # choose 可以是 'a','b' 或它们组成的列表
    choose: Literal["a", "b"] | list[Literal["a", "b"]]


# 节点a
def node_a(state: MyState):
    print("node_a")


# 节点b
def node_b(state: MyState):
    print("node_b")


# 创建 StateGraph 对象
builder = StateGraph(state_schema=MyState)

# 添加节点
builder.add_node(node_a)
builder.add_node(node_b)


# 路由选择函数，返回路由（节点）名称，可以是单个值，也可以是多个值
def choose_router(state: MyState):
    choose = state["choose"]
    if choose == "a":
        return "a"
    elif choose == "b":
        return "b"
    elif isinstance(choose, str):
        return "end"
    elif isinstance(choose, Iterable):
        result = []
        for item in choose:
            if item in ["a", "b"]:
                result.append(item)
        return result if result else "end"
    else:
        return "end"


# 添加条件边
# 第1个参数还是节点名称
# 第2个参数是路由选择函数
# 第3个参数路由名称和节点名的映射，如果都一样可省略
builder.add_conditional_edges(START, choose_router, {"a": "node_a", "b": "node_b", "end": END})
builder.add_edge("node_a", END)
builder.add_edge("node_b", END)

# 构建图
graph = builder.compile()

# 运行图
graph.invoke(input={"choose": "a"})
print("=" * 100)
graph.invoke(input={"choose": "c"})
print("=" * 100)
graph.invoke(input={"choose": ["a", "b", "c"]})
