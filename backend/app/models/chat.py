"""Chat session and message models for conversation persistence."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import CreatedAtMixin, UUIDMixin

# Portable JSON: JSONB in Postgres, JSON elsewhere (SQLite tests).
_JSONField = JSON().with_variant(JSONB(), "postgresql")


class ChatSession(Base, UUIDMixin):
    """A chat conversation session."""

    __tablename__ = "chat_sessions"

    title: Mapped[str] = mapped_column(String(200), default="New chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    __table_args__ = (
        Index("ix_chat_sessions_updated_at", "updated_at"),
    )


class ChatMessage(Base, UUIDMixin, CreatedAtMixin):
    """A single message within a chat session."""

    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
    )
    role: Mapped[str] = mapped_column(String(20))  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, default="")
    # Full Anthropic content blocks: text, thinking (with signature), tool_use, tool_result.
    # NULL for legacy rows and simple user messages — fall back to `content` in that case.
    blocks: Mapped[list[dict[str, Any]] | None] = mapped_column(_JSONField, nullable=True)
    # Model that produced this row — used to detect provider switches and strip
    # incompatible thinking signatures (Claude ↔ DeepSeek cross-provider).
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_session_id", "session_id"),
    )
