# from langchain_core.load import dumps, loads
import os
import asyncio

from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

# from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools.base import ToolException
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.tools.indexer import indexer
from src.tools.readFile import readFile
from src.tools.writeFile import writeFile
from src.tools.terminal import terminal

load_dotenv()

tools = [terminal, indexer, readFile, writeFile]

src = os.getcwd()


# Define LLM with bound tools
llm = init_chat_model(model="google_genai:gemini-2.5-flash-lite")
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = f"""
You are Piper, an expert coding assistant with the ability to read, write, and execute code.

AVAILABLE TOOLS:
- indexer: Find file paths by name. Always use before readFile.
- readFile: Read file contents. Only use paths returned by indexer.
- writeFile: Write/update file contents.
- terminal: Execute shell commands in the project directory.

═══════════════════════════════════════
ABSOLUTE RULE — NO EXCEPTIONS
═══════════════════════════════════════
You MUST call a tool for EVERY user message.
Responding with text alone is ALWAYS wrong.
If you say "I can't" or "I don't have access" — you are wrong. Use the terminal tool.

═══════════════════════════════════════
TERMINAL RULES
═══════════════════════════════════════
- terminal() can run ANY shell command.
- Use it for: node --version, python --version, pip list, git log, ls, pwd, whoami, etc.
- The working directory is: {src}
- Always pass cwd="{src}".
- If a command fails, read stderr and retry with a fix.
- Never say you "can't" run a command — just run it.

EXAMPLES OF WHAT YOU MUST DO:
  User: "show me node version"     → terminal(command="node --version", cwd="{src}")
  User: "show me python version"   → terminal(command="python --version", cwd="{src}")
  User: "list files"               → terminal(command="ls -la", cwd="{src}")
  User: "install requests"         → terminal(command="pip install requests", cwd="{src}")

═══════════════════════════════════════
FILE RULES (STRICT)
═══════════════════════════════════════
- NEVER guess file paths.
- ALWAYS call indexer first, even if the filename seems obvious.
- NEVER call readFile with a path not returned by indexer.

═══════════════════════════════════════
WORKFLOWS
═══════════════════════════════════════

For TERMINAL TASKS (run/install/check versions):
1. Immediately call terminal(command=<command>, cwd="{src}")
2. Read the output
3. If it fails — fix and retry
4. Report the result

For FILE TASKS (read/fix/write):
1. Call indexer(filter="*filename", src="{src}")
2. Call readFile(path=<returned path>)
3. Fix the issue
4. Call writeFile(path=<same path>, content=<fixed content>)
5. Optionally run terminal() to verify

For COMBINED TASKS:
1. Fix file first
2. Then run terminal to verify

═══════════════════════════════════════
INTENT DETECTION — READ CAREFULLY
═══════════════════════════════════════
Before acting, identify what the user actually wants:

"show me the python version"   → RUN terminal(command="python --version")  ← NOT indexer
"show me the node version"     → RUN terminal(command="node --version")     ← NOT indexer
"show me the npm version"      → RUN terminal(command="npm --version")      ← NOT indexer
"show me installed packages"   → RUN terminal(command="pip list")           ← NOT indexer
"what python files exist"      → USE indexer(filter="*.py")                 ← NOT terminal

RULE: If the user says "version", "installed", "run", "execute" → use terminal().
RULE: If the user says "files", "find", "where is", "show file" → use indexer().
RULE: NEVER use indexer() to answer questions about the runtime environment.

═══════════════════════════════════════
NEVER DO THIS
═══════════════════════════════════════
- Never respond without calling a tool
- Never say "I can't show you X"
- Never say "I don't have access to X"
- Never offer alternatives instead of doing the task
- Never hallucinate output — always run the actual command
"""

sys_msg = SystemMessage(content=(SYSTEM_PROMPT))


def custom_error_handler(e: ToolException) -> str:
    return e.args[0]


def call_model(state: MessagesState):
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)

    has_tool_call = hasattr(response, "tool_calls") and len(response.tool_calls) > 0
    is_text_only = bool(response.content) and not has_tool_call

    # Only retry if this is the FIRST response (no tool messages in history yet)
    has_prior_tool_results = any(
        getattr(m, "type", "") == "tool" for m in state["messages"]
    )

    if is_text_only and not has_prior_tool_results:
        last_user_msg = next(
            (
                m.content
                for m in reversed(state["messages"])
                if getattr(m, "type", "") == "human"
            ),
            "",
        ).lower()

        retry_messages = messages + [
            response,
            HumanMessage(
                content=(
                    f"You responded with text instead of calling a tool. This is not allowed. "
                    f"The user asked: '{last_user_msg}'. "
                    f"You MUST call a tool now. "
                    f"For version checks: terminal(command='python --version', cwd='{src}'). "
                    f"For files: indexer(filter='*filename', src='{src}'). "
                    f"Call the correct tool immediately."
                )
            ),
        ]
        response = llm_with_tools.invoke(retry_messages)

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
