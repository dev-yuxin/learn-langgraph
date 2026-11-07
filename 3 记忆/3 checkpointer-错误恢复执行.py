from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START, END

from langgraph.graph import StateGraph


# 状态类
class MyState(TypedDict):
    pass


# 控制b是否发生错误
is_b_error = True


# 节点a
def node_a(state: MyState):
    print("node_a start")
    print("node_a end")


# 节点b
def node_b(state: MyState):
    # 错误恢复执行是从整个节点重新执行，要保证之前的操作是幂等的
    print("node_b start")
    if is_b_error:
        raise Exception("node_b error")
    print("node_b end")


# 节点c
def node_c(state: MyState):
    print("node_c start")
    print("node_c end")


# 创建StateGraph对象
builder = StateGraph(state_schema=MyState)

# 添加节点
builder.add_node(node_a)
builder.add_node(node_b)
builder.add_node(node_c)

# 添加边
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", "node_c")
builder.add_edge("node_c", END)

# 编译图（使用内存记录checkpointer）
graph = builder.compile(checkpointer=InMemorySaver())

# 设置 thread_id
config = {
    "configurable": {
        "thread_id": "thread_1"
    }
}

# 第一次运行（会出错）
try:
    graph.invoke(input={}, config=config)
except Exception as e:
    print(e)
print("=" * 100)

# 第二次运行（input传入None，config传入相同thread_id）
is_b_error = False
graph.invoke(input=None, config=config)
