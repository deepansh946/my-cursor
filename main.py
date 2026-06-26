import json
import logging
from contextlib import asynccontextmanager

from pathlib import Path
import shutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel
from github import Github

from src.agent.graph import builder

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


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    github_token: str | None
    repo: str | None


def _thread_workspace(thread_id: str) -> Path:
    return Path(f"tmp/piper/{thread_id[:8]}")


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


def _serialize_checkpoint_messages(thread_id: str, messages: list) -> list[dict]:
    """Align checkpoint state with the UI message shape (same fields as SSE chunks)."""
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
                elif name in ("commit_changes", "create_pr"):
                    item["subtype"] = "git"
        out.append(item)
    return out


@app.delete("/thread/{thread_id}")
async def delete_thread(thread_id: str):
    clone_path = _thread_workspace(thread_id)
    if _checkpointer is None:
        raise HTTPException(status_code=503, detail="Checkpointer not ready")
    if clone_path.exists():
        shutil.rmtree(clone_path)
    await _checkpointer.adelete_thread(thread_id)
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


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    repo_path = _repo_path(request.thread_id, request.repo)
    input_data = {"messages": [HumanMessage(content=request.message)]}
    config = {"configurable": {"thread_id": request.thread_id, "repo_path": repo_path, "repo": request.repo, "github_token": request.github_token}}
    async def event_stream():
        try:
            async for message, metadata in graph.astream(
                input_data, config=config, stream_mode="messages"
            ):
                # Filter out empty or system messages
                if not message.content:
                    continue

                msg_type = (
                    message.__class__.__name__
                )  # AIMessage, ToolMessage, HumanMessage
                node = metadata.get("langgraph_node", "")

                chunk = {
                    "type": msg_type,
                    "content": _content_to_str(message.content),
                    "node": node,
                }

                # For ToolMessage, include tool name if available
                if hasattr(message, "name") and message.name:
                    chunk["tool_name"] = message.name

                    if message.name == "terminal":
                        chunk["subtype"] = "terminal"
                    elif message.name in ("commit_changes", "create_pr"):
                        chunk["subtype"] = "git"

                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")



@app.get("/github/repos")
async def get_github_repos(request: Request):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    g = Github(token)

    user = g.get_user()
    repos = [{"name": r.name, "full_name": r.full_name, "private": r.private, "html_url": r.html_url} for r in user.get_repos()]

    return {"repos": repos}