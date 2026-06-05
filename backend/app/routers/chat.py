"""Chat model endpoints and SSE route facade."""

import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.ai.model_catalog import list_available_models, save_preferred_model
from app.api_errors import bad_request
from app.routers.chat_streaming import reconnect_active_run, start_chat_stream
from app.schemas.ai.chat import ChatRequest

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/chat/models")
async def list_models():
    """Return all available models. DeepSeek models appear only when DEEPSEEK_API_KEY is set."""
    return await list_available_models()


@router.put("/chat/models/preferred")
async def set_preferred_model(body: dict):
    """Persist the user's preferred model so all AI features use it."""
    model_id = body.get("model")
    if not model_id or not isinstance(model_id, str):
        raise bad_request("Missing 'model' field")
    await save_preferred_model(model_id)
    return {"ok": True, "model": model_id}


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream AI agent response as SSE events, persisting full Anthropic blocks."""
    return await start_chat_stream(request)


@router.get("/chat/sessions/{session_id}/stream")
async def stream_active_run(session_id: uuid.UUID) -> StreamingResponse:
    """Reconnect to an in-progress agent run for this session."""
    return await reconnect_active_run(session_id)
