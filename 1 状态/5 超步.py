from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.constants import START, END


# 定义状态类
class MyState(TypedDict):
    pass


# 节点a
def node_a(state: MyState, config: RunnableConfig):
    print(config["metadata"]["langgraph_step"], "a")


# 节点b
def node_b(state: MyState, config: RunnableConfig):
    print(config["metadata"]["langgraph_step"], "b")


# 节点c
def node_c(state: MyState, config: RunnableConfig):
    print(config["metadata"]["langgraph_step"], "c")


# 节点d
def node_d(state: MyState, config: RunnableConfig):
    print(config["metadata"]["langgraph_step"], "d")


# 节点e
def node_e(state: MyState, config: RunnableConfig):
    print(config["metadata"]["langgraph_step"], "e")


# 创建 StateGraph对象
builder = StateGraph(state_schema=MyState)

"""
超步是 langgraph 执行最小单元，一个超步分为3个阶段
1. 计划阶段：决定路由到哪些节点。
2. 执行阶段：并行执行这些节点。
3. 提交阶段：把执行后的结果提交，进行状态规约。
START -> a → b → d → e -> END
         |           ↑
         ↓ → c -------
超步编号         执行节点
0               START
1               a
2               b, c
3               d, e
4               e, END
5               END
"""

# 添加节点
builder.add_node(node_a)
builder.add_node(node_b)
builder.add_node(node_c)
builder.add_node(node_d)
builder.add_node(node_e)

# 添加边
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", "node_d")
builder.add_edge("node_d", "node_e")
builder.add_edge("node_e", END)
builder.add_edge("node_a", "node_c")
builder.add_edge("node_c", "node_e")

# 编译图
graph = builder.compile()

# 运行图
graph.invoke(input={})
