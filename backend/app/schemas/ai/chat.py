"""Schemas for chat sessions and messages."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.base import CamelModel


# --- Request ---

class ChatMessageInput(BaseModel):
    role: str
    content: str


class ChatRequest(CamelModel):
    session_id: uuid.UUID | None = None
    messages: list[ChatMessageInput]
    model: str | None = None


class SessionCreate(CamelModel):
    title: str = "New chat"


class SessionUpdate(CamelModel):
    title: str


# --- Response ---

class ChatMessageResponse(CamelModel):
    id: uuid.UUID
    role: str
    content: str
    # Full Anthropic blocks (thinking/text/tool_use/tool_result) when available.
    # Frontend uses these to rebuild the timeline of thinking + tool steps on reload.
    blocks: list[dict[str, Any]] | None = None
    created_at: datetime


class SessionResponse(CamelModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message: str | None = None


class SessionDetailResponse(CamelModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse]
