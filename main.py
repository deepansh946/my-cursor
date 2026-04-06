import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel

from src.agent.graph import builder

graph = None
_checkpointer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, _checkpointer
    async with AsyncSqliteSaver.from_conn_string("piper.db") as checkpointer:
        _checkpointer = checkpointer
        graph = builder.compile(checkpointer=checkpointer)
        yield
        _checkpointer = None


app = FastAPI(title="Langgraph API", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    thread_id: str


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
        content = message.content
        if isinstance(content, list):
            content = json.dumps(content)
        elif not isinstance(content, str):
            content = str(content)
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
        out.append(item)
    return out


@app.delete("/thread/{thread_id}")
async def delete_thread(thread_id: str):
    if _checkpointer is None:
        raise HTTPException(status_code=503, detail="Checkpointer not ready")
    await _checkpointer.adelete_thread(thread_id)
    return {"ok": True}


@app.get("/thread/{thread_id}/messages")
def thread_messages(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snap = graph.get_state(config)
    except Exception:
        return {"messages": []}
    if snap is None or not snap.values:
        return {"messages": []}
    raw = snap.values.get("messages") or []
    return {"messages": _serialize_checkpoint_messages(thread_id, raw)}


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    input_data = {"messages": [request.message]}

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
                    "content": message.content,
                    "node": node,
                }

                # For ToolMessage, include tool name if available
                if hasattr(message, "name") and message.name:
                    chunk["tool_name"] = message.name

                    if message.name == "terminal":
                        chunk["subtype"] = "terminal"

                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
