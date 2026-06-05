"""Persistence helpers for chat stream workers."""

import uuid
from datetime import datetime, timedelta

from app.database import get_session
from app.models.chat import ChatMessage


async def persist_assistant_row(
    session_id: uuid.UUID,
    blocks: list[dict],
    model: str,
    created_at: datetime,
) -> str:
    """Persist one assistant iteration and return its text content."""
    text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    text = "".join(text_parts)
    async with get_session() as save_db:
        save_db.add(ChatMessage(
            session_id=session_id,
            role="assistant",
            content=text,
            blocks=blocks,
            model=model,
            created_at=created_at,
        ))
    return text


async def persist_tool_result_row(
    session_id: uuid.UUID,
    blocks: list[dict],
    base_time: datetime,
    msg_index: int,
) -> None:
    """Persist one tool-result batch as a user row."""
    async with get_session() as save_db:
        save_db.add(ChatMessage(
            session_id=session_id,
            role="user",
            content="",
            blocks=blocks,
            created_at=base_time + timedelta(microseconds=msg_index),
        ))
