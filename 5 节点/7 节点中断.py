from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command


# 状态类
class MyState(TypedDict):
    name: str
    age: int


# 姓名节点
def name_node(state: MyState):
    # 中断
    name = interrupt("请输入姓名")
    name = name.strip()
    return {
        "name": name
    }


# 年龄节点
def age_node(state: MyState):
    # 中断
    age = interrupt("请输入年龄")
    age = int(age.strip())
    return {
        "age": age
    }


# 创建 StateGraph 对象
builder = StateGraph(MyState)

# 添加节点
builder.add_node(name_node)
builder.add_node(age_node)

# 添加边
builder.add_edge(START, "name_node")
builder.add_edge(START, "age_node")
builder.add_edge("name_node", END)
builder.add_edge("age_node", END)

# 构建图
# 中断是基于checkpointer的
graph = builder.compile(checkpointer=InMemorySaver())

# 设置 thread_id
config = {
    "configurable": {
        "thread_id": "thread_1"
    }
}

# 运行
output_state = graph.invoke(input={}, config=config)
interrupts = output_state["__interrupt__"]
print(interrupts)

# 要和 interrupts 一一对应
resume_map = {}
for interr in interrupts:
    resume_map[interr.id] = input(interr.value)

# 中断恢复
output_state = graph.invoke(input=Command(resume=resume_map), config=config)
print(output_state)
