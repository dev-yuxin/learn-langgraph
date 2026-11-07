from typing import TypedDict
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.store.sqlite import SqliteStore
from langgraph.runtime import Runtime

"""
短期记忆：
    当前会话中直接进入模型上下文窗口的信息，比如最近几轮对话、系统提示、工具结果。
    短期记忆依赖于会话id
    langchain和langgraph中短期记忆是指checkpointer，可以存内存里，也可以存数据库
长期记忆：
    存在模型上下文之外、跨会话持久保留、需要时检索回来的信息，比如用户偏好、历史摘要、事实档案、知识片段。
    长期记忆是跨会话的
    langchain和langgraph中长期记忆是指store，可以存内存里，也可以存数据库
"""

# 使用 sqlite 轻量级数据库（仅作为demo）作为 store
with SqliteStore.from_conn_string("./sqlite-store") as store:
    # 首次执行必须调用
    store.setup()
    # 往 store 中存入数据
    # namespace是元组，value是字典
    store.put(
        namespace=("user", "zhangsan"),
        key="PREFERENCE",
        value={"hobbies": ["唱", "跳", "篮球"]}
    )
    store.put(
        namespace=("user", "lisi"),
        key="PREFERENCE",
        value={"hobbies": ["游戏", "动漫"]}
    )


# 状态类
class MyState(TypedDict):
    recommend: list[str]


# 推荐节点
def recommend_node(state: MyState, runtime: Runtime):
    # 从运行时上下文中获取用户名
    username = runtime.context.get("username", "")
    # 获取长期记忆
    with SqliteStore.from_conn_string("./sqlite-store") as store:
        store.setup()
        item = store.get(namespace=("user", username), key="PREFERENCE")
        hobbies = []
        if item:
            hobbies = item.value.get("hobbies", [])
        return {
            "recommend": hobbies
        }


# 创建 StateGraph 对象
builder = StateGraph(state_schema=MyState)

# 添加节点
builder.add_node(recommend_node)

# 添加边
builder.add_edge(START, "recommend_node")
builder.add_edge("recommend_node", END)

# 编译图
graph = builder.compile()

# 运行图
# 传入 context 运行时上下文，只在本次运行时有效
output_state = graph.invoke(input={}, context={"username": "zhangsan"})
print(output_state)
