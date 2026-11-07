from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START, END

from langgraph.graph import StateGraph


# 子图状态
class SubState(TypedDict):
    pass


# 子图节点 b1
def node_b1(state: SubState):
    print("node_b1")


# 子图节点 b2
def node_b2(state: SubState):
    print("node_b2")


# 创建子图 StateGraph 对象
sub_builder = StateGraph(SubState)

# 子图添加节点
sub_builder.add_node(node_b1)
sub_builder.add_node(node_b2)

# 子图添加边
sub_builder.add_edge(START, "node_b1")
sub_builder.add_edge("node_b1", "node_b2")
sub_builder.add_edge("node_b2", END)

# 编译子图
# 当父图开启检查点后，子图检查点有以下3种情况
# None(继承父图检查点，默认，一般用的最多): 子图可以中断，子图没有自己的记忆，每次进入子图子图状态都是新的
# True(子图独立开启检查点): 子图可以中断，子图有自己的记忆，每次进入子图保留上一次状态
# False(子图不使用检查点): 子图无法中断，子图部分没有记忆
sub_graph = sub_builder.compile()


# 父图状态
class MyState(TypedDict):
    pass


# 父节点a
def node_a(state: MyState):
    print("node_a")


# 父节点b
def node_b(state: MyState):
    # 在父节点中调用子图
    sub_graph.invoke(input={})


# 父节点c
def node_c(state: MyState):
    print("node_c")


# 创建父图 StateGraph 对象
builder = StateGraph(MyState)

# 父图添加节点
builder.add_node(node_a)
builder.add_node(node_b)
builder.add_node(node_c)

# 父图添加边
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", "node_c")
builder.add_edge("node_c", END)

# 编译父图
graph = builder.compile(checkpointer=InMemorySaver())

# 调用父图
graph.invoke(input={})
