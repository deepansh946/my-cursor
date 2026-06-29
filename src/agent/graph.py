# from langchain_core.load import dumps, loads
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI


# from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langchain_core.tools.base import ToolException
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.tools.indexer import indexer
from src.tools.readFile import readFile
from src.tools.terminal import terminal
from src.tools.writeFile import writeFile
from src.tools.github_tools import clone_repo, commit_changes, create_pr
from src.agent.prompt import build_system_prompt
from src.agent.usage import get_usage, merge_usage

# from src.tools.stackoverflow import stackoverflow

load_dotenv()

tools = [terminal, indexer, readFile, writeFile, clone_repo, commit_changes, create_pr]

src = os.getcwd()

# 1. Initialize the primary model (e.g., Anthropic Claude)
primary_model = init_chat_model(
    model="google_genai:gemini-2.5-flash",
)

# 2. Initialize the backup fallback model (e.g., OpenAI GPT)
backup_model = init_chat_model(
    model="google_genai:gemini-2.5-flash-lite",
)


llm_with_fallback = primary_model.with_fallbacks([backup_model])

llm_with_tools = llm_with_fallback.bind_tools(tools)

def custom_error_handler(e: ToolException) -> str:
    return e.args[0] if e.args else "Tool execution failed."


def call_model(state: MessagesState, config: RunnableConfig):
    cfg = config.get("configurable", {})
    repo_path = cfg.get("repo_path")
    workspace = repo_path if repo_path else src
    has_repo = bool(cfg.get("repo"))
    sys_msg = SystemMessage(content=build_system_prompt(workspace, has_repo))
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages, config=config)

    usage_metadata = getattr(response, 'usage_metadata', None)

    if usage_metadata:
        merge_usage(config, usage_metadata)

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
    {"tools": "tools", END: END},
)
builder.add_edge("tools", "model")
