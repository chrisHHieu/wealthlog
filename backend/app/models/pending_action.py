"""Deferred write actions awaiting explicit user confirmation.

When the AI agent calls a financial *write* tool (create/update/delete a
transaction), the harness does not execute it inline. Instead it persists the
intended call here and tells the agent the action is pending. The user confirms
(or rejects) it through a dedicated endpoint, which is the moment the write
actually runs. This makes "the user agreed to this change" a mechanical gate
rather than a verbal instruction in the prompt — the load-bearing guardrail for
an app that lets an LLM move money.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin

# Portable JSON: JSONB in Postgres, JSON elsewhere (SQLite tests).
_JSONField = JSON().with_variant(JSONB(), "postgresql")


class PendingAction(Base, UUIDMixin):
    """One deferred write-tool call awaiting user confirmation."""

    __tablename__ = "pending_actions"

    # Nullable: the originating session may be deleted before resolution.
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True,
    )
    tool_name: Mapped[str] = mapped_column(String(100))
    arguments: Mapped[dict[str, Any]] = mapped_column(_JSONField, default=dict)
    # Human-readable {summary, items} the confirmation card renders instead of
    # raw arguments — resolves UUIDs to descriptions and shows old → new diffs.
    # Nullable: best-effort, and older rows predate it.
    preview: Mapped[dict[str, Any] | None] = mapped_column(_JSONField, nullable=True)
    # pending → executed | rejected | failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # Tool output text once executed (or the failure message).
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index("ix_pending_actions_session_status", "session_id", "status"),
    )
