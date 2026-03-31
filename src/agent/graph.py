# from langchain_core.load import dumps, loads
import datetime

from langchain.chat_models import init_chat_model

# from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import Literal

from src.tools.indexer import indexer
from src.tools.readFile import readFile
from src.tools.writeFile import writeFile

tools = [indexer, readFile, writeFile]


class State(MessagesState):
    summary: str


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

CRITICAL RULE:
- You are NOT allowed to call readFile unless the path was returned by indexer.
- Any path not coming from indexer is INVALID.
- Always call indexer first even if the filename looks obvious.

Workflow:
1. Call indexer with filter="*filename" and src as the current working directory
2. Use returned path
3. Call readFile
4. Fix bugs
5. Call writeFile

If you do not call tools, your answer is incorrect.
"""

sys_msg = SystemMessage(content=(SYSTEM_PROMPT))


def call_model(state: State):

    summary = state.get("summary", "")

    if summary:
        system_message = f"Summary of the above conversation: {summary}"
        messages = [SystemMessage(content=system_message)] + state["messages"]

    else:
        messages = state["messages"]

    response = llm_with_tools.invoke(messages)

    return {"messages": response}


def summarize_conversation(state: State):

    summary = state.get("summary", "")

    if summary:
        summary_message = (
            f"This is the summary to date: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )

    else:
        summary_message = "Create a summary of the conversation above:"

    messages = state["messages"] + [HumanMessage(content=summary_message)]

    response = llm_with_tools.invoke(messages)

    # Delete all but the 2 most recent messages
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    return {"summary": response.content, "messages": delete_messages}


# Determine whether to end or summarize the conversation
def should_continue(state: State) -> Literal["summarize_conversation", END]:
    """Return the next node to execute."""

    messages = state["messages"]

    # If there are more than six messages, then we summarize the conversation
    if len(messages) > 6:
        return "summarize_conversation"

    # Otherwise we can just end
    return END


# Build graph
builder = StateGraph(MessagesState)
builder.add_node("tools", ToolNode(tools))
builder.add_node("summarize_conversation", summarize_conversation)
builder.add_node("call_model", call_model)
builder.add_edge(START, "call_model")
builder.add_conditional_edges(
    "call_model",
    tools_condition,
)
builder.add_conditional_edges(
    "call_model",
    should_continue,
)
builder.add_edge("summarize_conversation", "call_model")
builder.add_edge("tools", "call_model")

# Compile graph
graph = builder.compile()
print(datetime.datetime.now(), "----------------------------------------------")
