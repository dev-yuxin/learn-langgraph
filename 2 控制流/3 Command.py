from typing import TypedDict, Literal, Iterable
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import Command


# 状态类
class MyState(TypedDict):
    choose: Literal["a", "b"]
    a: bool
    b: bool


# 选择节点
def choose_node(state: MyState):
    choose = state["choose"]
    if choose == "a":
        # 使用 Command 可以手动控制跳转到哪个节点，同时增量更新状态
        return Command(
            goto="node_a",
            update={
                "b": False
            }
        )
    elif choose == "b":
        return Command(
            goto="node_b",
            update={
                "a": False
            }
        )
    else:
        return Command(
            goto=END,
            update={
                "a": False,
                "b": False
            }
        )


# 节点a
def node_a(state: MyState):
    return {
        "a": True,
    }


# 节点b
def node_b(state: MyState):
    return {
        "b": True,
    }


# 创建StateGraph
builder = StateGraph(state_schema=MyState)

# 添加节点
builder.add_node(choose_node)
builder.add_node(node_a)
builder.add_node(node_b)

# 添加边
builder.add_edge(START, "choose_node")
# 注意，这里由于已经有Command了，不用再添加条件边了
builder.add_edge("node_a", END)
builder.add_edge("node_b", END)

# 编译
graph = builder.compile()

# 运行
output_state = graph.invoke(input={"choose": "a"})
print(output_state)
print("=" * 100)
output_state = graph.invoke(input={"choose": "c"})
print(output_state)
