from typing import TypedDict, Annotated
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from operator import add


def my_reducer(left, right):
    """
    自定义规约函数
    :param left: 当前值
    :param right: 增量更新的值
    :return: 规约后的值
    """
    return left + right


# 全局状态类
class MyState(TypedDict):
    # 默认情况下，不设置规约函数，将会是覆盖操作
    a: list[str]
    # 设置了规约函数，则以规约函数规约
    b: Annotated[list[str], my_reducer]
    # 同一超步多个节点并行对同一字段进行操作，必须设置规约函数
    # add: python 内置的规约函数，处理常用的累加操作
    c: Annotated[list[str], add]


# 节点a
def node_a(state: MyState):
    return {
        "a": ["a"],
        "c": ["c"]
    }


# 节点b
def node_b(state: MyState):
    return {
        "b": ["b"],
        "c": ["c"]
    }


# 创建StateGraph对象
builder = StateGraph(MyState)

# 添加节点
builder.add_node(node_a)
builder.add_node(node_b)

# 添加边
builder.add_edge(START, "node_a")
builder.add_edge(START, "node_b")
builder.add_edge("node_a", END)
builder.add_edge("node_b", END)

# 编译和运行
graph = builder.compile()
output_state = graph.invoke({
    "a": ["hello"],
    "b": ["hello"],
})
print(output_state)
