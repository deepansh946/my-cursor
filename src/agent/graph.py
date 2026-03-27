# from langchain_core.load import dumps, loads
import os
import datetime

from langchain.chat_models import init_chat_model

# from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.tools.indexer import indexer
from src.tools.readFile import readFile
from src.tools.writeFile import writeFile


tools = [readFile, writeFile]


# Define LLM with bound tools
llm = init_chat_model(model="google_genai:gemini-2.5-flash-lite")
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """
Hello your name is Enigma, you are a helpful coding assistant. Whenever any file is provided to you, you will analyze the file and give 3 bug fixes for the file. Use the fileLocations string to get all the locations of every file.

Tools Usage Instructions:
- You'll access the file and use the readFile tool to read the file using the location and send the whole file to LLM.
- Then after the bugs are fixed in the file and use the writeTool to write the file on the same location.
"""

# System message
fileLocations = indexer()

FILE_LOCATION_INSTRUCTION = f"\nUse the below string to get the file locations of every file {str(fileLocations)}"
sys_msg = SystemMessage(content=(SYSTEM_PROMPT + FILE_LOCATION_INSTRUCTION))


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
