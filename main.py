from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from agent.graph import graph

app = FastAPI(title="Langgraph API")


class ChatRequest(BaseModel):
    message: str
    thread_id: str


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

                chunk = {
                    "type": msg_type,
                    "content": message.content,
                    "node": metadata.get("langgraph_node", ""),
                }

                # For ToolMessage, include tool name if available
                if hasattr(message, "name") and message.name:
                    chunk["tool_name"] = message.name

                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
