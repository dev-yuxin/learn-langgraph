import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, MessagesState
from langgraph.constants import START, END
from langgraph.types import RetryPolicy

load_dotenv(override=True)


# 状态定义
class MyState(MessagesState):
    query: str
    answer: str


# 输入节点
def input_node(state: MyState):
    return {
        "query": state["query"],
        "messages": [HumanMessage(content=state["query"])]
    }


attempt = 0

# 大模型
llm = init_chat_model(
    api_key=os.getenv("bailian_api_key"),
    base_url="https://www.baidu.com",  # 故意写错
    model_provider="openai",
    model="qwen-flash",
    timeout=5,
    configurable_fields=["base_url"]
)


# 大模型节点
def llm_node(state: MyState):
    # 前2次都会发生网络错误，第3次修正
    global attempt
    attempt += 1
    print(f"llm_node 第{attempt}次执行")
    if attempt < 3:
        ai_message = llm.invoke(input=state["messages"])
    else:
        ai_message = llm.invoke(input=state["query"], config={"base_url": os.getenv("bailian_base_url")})
    return {
        "messages": [ai_message],
        "answer": ai_message.content
    }


# 创建 StateGraph 对象
builder = StateGraph(MyState)

# 添加节点
builder.add_node(input_node)
# 节点重试机制
# 如果发生代码逻辑错误不会重试，发生的是例如网络连接错误会重试
builder.add_node(llm_node, retry_policy=RetryPolicy(max_attempts=3))

# 添加边
builder.add_edge(START, "input_node")
builder.add_edge("input_node", "llm_node")
builder.add_edge("llm_node", END)

# 编译图
graph = builder.compile()

# 运行图
try:
    output_state = graph.invoke({
        "query": "你好，你是谁"
    })
    print(output_state)
except Exception as e:
    print(e)
