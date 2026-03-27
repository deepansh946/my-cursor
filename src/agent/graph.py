# from langchain_core.load import dumps, loads
import datetime
import os

from langchain.chat_models import init_chat_model

# from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.tools.indexer import indexer
from src.tools.readFile import readFile
from src.tools.writeFile import writeFile

tools = [indexer, readFile, writeFile]


# Define LLM with bound tools
llm = init_chat_model(model="google_genai:gemini-2.5-flash-lite")
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """
Hello your name is Piper, you are a helpful coding assistant.

IMPORTANT RULES:

- You MUST NOT guess file paths.
- Call indexer ONLY if you do not already have the file path.
- Do NOT call indexer again if results are already available.
- Do NOT answer without calling tools.

Workflow:
1. Call indexer with filter="*filename"
2. Use returned path
3. Call readFile
4. Fix bugs
5. Call writeFile

If you do not call tools, your answer is incorrect.
"""

sys_msg = SystemMessage(content=(SYSTEM_PROMPT))


# Node
def assistant(state: MessagesState):
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}


# Build graph
builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", "assistant")

# Compile graph
graph = builder.compile()
print(datetime.datetime.now(), "----------------------------------------------")
