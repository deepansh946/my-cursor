# from langchain_core.load import dumps, loads
import datetime
import os

from langchain.chat_models import init_chat_model

# from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langchain_core.tools.base import ToolException
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.tools.indexer import indexer
from src.tools.readFile import readFile
from src.tools.writeFile import writeFile

tools = [indexer, readFile, writeFile]

src = os.getcwd()


class State(MessagesState):
    summary: str


# Define LLM with bound tools
llm = init_chat_model(model="google_genai:gemini-2.5-flash-lite")
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = f"""
Hello your name is Piper, you are a helpful coding assistant.

IMPORTANT RULES:

- You MUST NOT guess file paths.
- Call indexer ONLY if you do not already have the file path.
- Do NOT call indexer again if results are already available.
- Do NOT answer without calling tools.

CRITICAL RULE:
- You are NOT allowed to call readFile unless the path was returned by indexer.
- Any path not coming from indexer is INVALID.
- Always call indexer first even if the filename looks obvious.

Workflow:
1. Call indexer with filter="*filename" and src as the {src}
2. Use returned path
3. Call readFile
4. Fix bugs
5. Call writeFile

If you do not call tools, your answer is incorrect.
"""

sys_msg = SystemMessage(content=(SYSTEM_PROMPT))


def custom_error_handler(e: ToolException) -> str:
    return e.args[0]


def call_model(state: State):

    messages = [sys_msg] + state["messages"]

    response = llm_with_tools.invoke(messages)

    return {"messages": response}


# Build graph
builder = StateGraph(MessagesState)
builder.add_node(
    "tools",
    ToolNode(tools, handle_tool_errors=custom_error_handler),
)
builder.add_node("model", call_model)
builder.add_edge(START, "model")
builder.add_conditional_edges(
    "model",
    tools_condition,
)
builder.add_edge("tools", "model")

# Compile graph
graph = builder.compile()
print(datetime.datetime.now(), "----------------------------------------------")
