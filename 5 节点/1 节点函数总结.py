from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime


# 状态类
class MyState(TypedDict):
    pass


# 节点函数
def test_node(state: MyState, config: RunnableConfig, runtime: Runtime):
    """
    Args: 通过类型注解在运行时注入，最少包含state1个参数，最多3个参数
        state: 上一个超步输出的状态，拿到的是快照，多个并行节点之间互不影响
        config: 传入的配置信息，包括 thread_id, 超步编号等
        runtime: 运行时信息，包括 store, context, stream_writer
    Returns:
        返回增量更新的state
    """