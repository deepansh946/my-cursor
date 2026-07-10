# from langchain_core.load import dumps, loads
import logging
import os

from dotenv import load_dotenv

# from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools.base import ToolException
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.agent.models import (
    COMPLEX_MODEL_ID,
    DEFAULT_MODEL_ID,
    SIMPLE_MODEL_ID,
    classify_complexity,
    get_llm,
)
from src.agent.prompt import build_system_prompt
from src.agent.usage import merge_usage
from src.tools.github_tools import clone_repo, commit_changes, create_pr
from src.tools.indexer import indexer
from src.tools.readFile import readFile
from src.tools.terminal import terminal
from src.tools.writeFile import writeFile

# from src.tools.stackoverflow import stackoverflow

load_dotenv()

logger = logging.getLogger(__name__)

tools = [terminal, indexer, readFile, writeFile, clone_repo, commit_changes, create_pr]

src = os.getcwd()


def custom_error_handler(e: ToolException) -> str:
    return e.args[0] if e.args else "Tool execution failed."


def call_model(state: MessagesState, config: RunnableConfig):
    cfg = config.get("configurable", {})
    repo_path = cfg.get("repo_path")
    workspace = repo_path if repo_path else src
    has_repo = bool(cfg.get("repo"))
    model_id = cfg.get("model_id") or DEFAULT_MODEL_ID

    if model_id == "auto":
        last_human = next(
            (m for m in reversed(state["messages"]) if getattr(m, "type", "") == "human"),
            None,
        )
        text = last_human.content if last_human else ""
        if not isinstance(text, str):
            if isinstance(text, list):
                text = " ".join(
                    b.get("text", "") for b in text if isinstance(b, dict)
                )
            else:
                text = str(text)
        model_id = classify_complexity(text or "", has_repo=has_repo)

    logger.debug("Using model: %s", model_id)
    primary = get_llm(model_id)
    fallback_id = SIMPLE_MODEL_ID if model_id != SIMPLE_MODEL_ID else COMPLEX_MODEL_ID
    llm_with_tools = primary.with_fallbacks([get_llm(fallback_id)]).bind_tools(tools)
    sys_msg = SystemMessage(content=build_system_prompt(workspace, has_repo))
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages, config=config)

    usage_metadata = getattr(response, "usage_metadata", None)

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
