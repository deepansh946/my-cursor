import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from github import Github
from langchain_core.messages import HumanMessage
from langchain_core.tools.base import ToolException
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel

from src.agent.graph import builder
from src.agent.models import DEFAULT_MODEL_ID, is_allowed_model, list_models
from src.agent.usage import clear_usage, get_usage, set_empty_usage
from src.tools.github_tools import clone_repo
from src.tools.paths import display_path

logger = logging.getLogger(__name__)

_API_DIR = Path(__file__).resolve().parent
_CHECKPOINT_DB = str(_API_DIR / "piper.db")

graph = None
_checkpointer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, _checkpointer
    async with AsyncSqliteSaver.from_conn_string(_CHECKPOINT_DB) as checkpointer:
        _checkpointer = checkpointer
        graph = builder.compile(checkpointer=checkpointer)
        yield
        _checkpointer = None


app = FastAPI(title="Langgraph API", lifespan=lifespan)

_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    github_token: str | None
    repo: str | None
    model_id: str | None


class CloneRequest(BaseModel):
    repo: str
    github_token: str | None


_THREAD_ID_RE = re.compile(r"^[A-Za-z0-9\-]{1,64}$")


def _thread_workspace(thread_id: str) -> Path:
    if not _THREAD_ID_RE.match(thread_id):
        raise HTTPException(status_code=400, detail="Invalid thread ID")
    return Path(f"tmp/piper/{thread_id}")


def _repo_path(thread_id: str, repo: str | None) -> str | None:
    if not repo:
        return None
    slug = repo.replace("/", "_")
    return str(_thread_workspace(thread_id) / slug)


def _content_to_str(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if isinstance(text, str):
                    parts.append(text)
                else:
                    parts.append(str(block))
            else:
                parts.append(str(block))
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def _format_tool_target(tool_name: str | None, args: dict | None) -> str | None:
    if not tool_name or not args:
        return None
    if tool_name in ("readFile", "writeFile", "editFile"):
        src = args.get("src")
        return display_path(str(src)) if src else None
    if tool_name == "create_file":
        fp = args.get("file_path")
        return display_path(str(fp)) if fp else None
    if tool_name == "indexer":
        filt = args.get("filter")
        return str(filt) if filt else None
    if tool_name == "terminal":
        cmd = args.get("command")
        if not cmd:
            return None
        text = str(cmd)
        return text if len(text) <= 60 else f"{text[:57]}..."
    if tool_name == "commit_changes":
        fp = args.get("file_path")
        return display_path(str(fp)) if fp else None
    if tool_name == "create_pr":
        title = args.get("title")
        return str(title) if title else None
    return None


def _tool_calls_from_message(message) -> list[dict]:
    raw = getattr(message, "tool_calls", None) or []
    out: list[dict] = []
    for tc in raw:
        if not isinstance(tc, dict):
            continue
        name = tc.get("name")
        args = tc.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        call_id = tc.get("id")
        if not name or not call_id:
            continue
        out.append({"id": call_id, "name": name, "args": args})
    return out


def _tool_call_id_args_map(messages: list) -> dict[str, tuple[str, dict]]:
    mapping: dict[str, tuple[str, dict]] = {}
    for message in messages:
        if getattr(message, "type", None) != "ai":
            continue
        for tc in _tool_calls_from_message(message):
            mapping[tc["id"]] = (tc["name"], tc["args"])
    return mapping


def _tool_call_chunks(message) -> list[dict]:
    chunks: list[dict] = []
    for tc in _tool_calls_from_message(message):
        target = _format_tool_target(tc["name"], tc["args"])
        chunk: dict = {
            "type": "tool_call",
            "tool_call_id": tc["id"],
            "tool_name": tc["name"],
        }
        if target:
            chunk["tool_target"] = target
        chunks.append(chunk)
    return chunks


def _serialize_checkpoint_messages(thread_id: str, messages: list) -> list[dict]:
    """Align checkpoint state with the UI message shape (same fields as SSE chunks)."""
    tool_args_map = _tool_call_id_args_map(messages)
    out: list[dict] = []
    idx = 0
    for message in messages:
        type = getattr(message, "type", None) or ""
        if type == "system":
            continue
        if type == "ai":
            content = message.content or ""
            if isinstance(content, str) and not content.strip():
                tool_calls = getattr(message, "tool_calls", None) or []
                if tool_calls:
                    continue
        type_name = {
            "human": "HumanMessage",
            "ai": "AIMessage",
            "tool": "ToolMessage",
        }.get(type)
        if not type_name:
            continue
        content = _content_to_str(message.content)
        item: dict = {
            "id": f"{thread_id}-cp-{idx}",
            "type": type_name,
            "content": content,
        }
        idx += 1
        if type == "tool":
            name = getattr(message, "name", None)
            if name:
                item["tool_name"] = name
                if name == "terminal":
                    item["subtype"] = "terminal"
                elif name in ("commit_changes", "create_pr", "create_file"):
                    item["subtype"] = "git"
            call_id = getattr(message, "tool_call_id", None)
            if call_id:
                item["tool_call_id"] = call_id
                tc_name, tc_args = tool_args_map.get(call_id, (name, {}))
                target = _format_tool_target(tc_name or name, tc_args)
                if target:
                    item["tool_target"] = target
        out.append(item)
    return out


def _graph_config(
    thread_id: str,
    model_id: str | None,
    repo: str | None,
    github_token: str | None,
) -> dict:
    repo_path = _repo_path(thread_id, repo)
    return {
        "configurable": {
            "thread_id": thread_id,
            "repo_path": repo_path,
            "repo": repo,
            "github_token": github_token,
            "model_id": model_id or DEFAULT_MODEL_ID,
        }
    }


def _message_chunk(message, metadata: dict) -> dict | None:
    content = _content_to_str(message.content)
    if not content.strip():
        return None
    msg_type = message.__class__.__name__
    chunk: dict = {
        "type": msg_type,
        "content": content,
        "node": metadata.get("langgraph_node", ""),
    }
    if hasattr(message, "name") and message.name:
        chunk["tool_name"] = message.name
        if message.name == "terminal":
            chunk["subtype"] = "terminal"
        elif message.name in ("commit_changes", "create_pr", "create_file"):
            chunk["subtype"] = "git"
    if hasattr(message, "tool_call_id") and message.tool_call_id:
        chunk["tool_call_id"] = message.tool_call_id
    return chunk


async def _stream_graph(graph_input, config: dict):
    try:
        async for message, metadata in graph.astream(
            graph_input,
            config=config,
            stream_mode="messages",
        ):
            for tc_chunk in _tool_call_chunks(message):
                yield tc_chunk
            chunk = _message_chunk(message, metadata)
            if chunk:
                yield chunk
    except Exception as e:
        yield {"type": "error", "content": str(e)}
    finally:
        usage_data = get_usage(config)
        if usage_data.get("input_tokens") or usage_data.get("output_tokens"):
            yield {
                "type": "usage",
                "input_tokens": usage_data.get("input_tokens", 0),
                "output_tokens": usage_data.get("output_tokens", 0),
                "total_tokens": usage_data.get("total_tokens", 0),
            }

        yield {"type": "done"}


def _git_repo_status(repo_path: str) -> dict:
    root = Path(repo_path)
    if not (root / ".git").exists():
        return {"cloned": False}

    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

    try:
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        commit = run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
        porcelain = run(["git", "status", "--porcelain"]).stdout.strip()
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or str(e)).strip()
        raise HTTPException(status_code=500, detail=f"Git status failed: {detail}")

    changes: list[str] = []
    if porcelain:
        for line in porcelain.splitlines()[:8]:
            if len(line) < 4:
                continue
            status = line[:2].strip() or "?"
            path = line[3:].strip()
            changes.append(f"{status} {path}")

    return {
        "cloned": True,
        "branch": branch,
        "commit": commit,
        "dirty": bool(porcelain),
        "changed_count": len(porcelain.splitlines()) if porcelain else 0,
        "changes": changes,
    }


@app.delete("/thread/{thread_id}")
async def delete_thread(thread_id: str):
    clone_path = _thread_workspace(thread_id)
    if _checkpointer is None:
        raise HTTPException(status_code=503, detail="Checkpointer not ready")
    if clone_path.exists():
        shutil.rmtree(clone_path)
    await _checkpointer.adelete_thread(thread_id)
    clear_usage(thread_id)
    return {"ok": True}


@app.get("/thread/{thread_id}/messages")
async def thread_messages(thread_id: str):
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not ready")
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snap = await graph.aget_state(config)
    except Exception:
        logger.exception("Failed to load checkpoint for thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to load messages")
    if snap is None or not snap.values:
        return {"messages": []}
    raw = snap.values.get("messages") or []
    return {"messages": _serialize_checkpoint_messages(thread_id, raw)}


@app.get("/thread/{thread_id}/repo-status")
async def thread_repo_status(thread_id: str, repo: str):
    if not repo:
        raise HTTPException(status_code=400, detail="Missing repo")
    repo_path = _repo_path(thread_id, repo)
    if not repo_path:
        return {"cloned": False}
    return await asyncio.to_thread(_git_repo_status, repo_path)


@app.post("/thread/{thread_id}/clone")
async def clone_thread_repo(thread_id: str, request: CloneRequest):
    config = _graph_config(thread_id, DEFAULT_MODEL_ID, request.repo, request.github_token)
    try:
        result = await asyncio.to_thread(clone_repo.invoke, {}, config=config)
        return {"ok": True, "message": result}
    except ToolException as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    model_id = request.model_id or DEFAULT_MODEL_ID
    if not is_allowed_model(model_id):
        raise HTTPException(status_code=400, detail="Invalid model ID")
    config = _graph_config(
        request.thread_id, model_id, request.repo, request.github_token
    )
    set_empty_usage(config)
    input_data = {"messages": [HumanMessage(content=request.message)]}

    async def event_stream():
        async for chunk in _stream_graph(input_data, config):
            if not chunk:
                continue
            if chunk.get("type") == "done":
                yield "data: [DONE]\n\n"
            else:
                yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/github/repos")
async def get_github_repos(request: Request):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    g = Github(token)
    user = g.get_user()
    repos = [
        {
            "name": r.name,
            "full_name": r.full_name,
            "private": r.private,
            "html_url": r.html_url,
        }
        for r in user.get_repos()
    ]

    return {"repos": repos}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/models")
async def get_models():
    return {"models": list_models(), "default": DEFAULT_MODEL_ID}
