from typing import TypedDict, Annotated
from operator import add
from langgraph.constants import START, END
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError
from langgraph.graph import StateGraph
from langgraph.managed import RemainingSteps, IsLastStep
from langgraph.types import Command


# 状态类
class MyState(TypedDict):
    count: Annotated[int, add]
    # langgraph 会通过类型注解自动注入
    remaining_steps: RemainingSteps
    is_last_step: IsLastStep


# 自增节点
def increament_node(state: MyState, config: RunnableConfig):
    print("当前超步: ", config["metadata"]["langgraph_step"], "当前state: ", state)
    # 当前超步 >= limit（即 remaining_steps <= 0）时会抛 GraphRecursionError 异常
    # 我们可以主动退出
    if state["is_last_step"]:
        return Command(goto=END)
    else:
        return Command(
            goto="increament_node",
            update={
                "count": 1
            }
        )


# 创建 StateGraph 对象
builder = StateGraph(state_schema=MyState)

# 添加节点
builder.add_node(increament_node)

# 添加边
builder.add_edge(START, "increament_node")

# 构建图
graph = builder.compile()

# 运行图
try:
    output_state = graph.invoke(
        input={"count": 0},
        # 设置递归循环限制，最多执行6个超步
        config={"recursion_limit": 6}
    )
except GraphRecursionError as e:
    print(e)
