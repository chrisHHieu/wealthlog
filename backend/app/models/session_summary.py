"""Episodic memory — one narrative summary per past ChatSession."""

import uuid

from sqlalchemy import JSON, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

# Portable JSON: JSONB in Postgres (indexable, faster), JSON elsewhere (SQLite tests).
_JSONField = JSON().with_variant(JSONB(), "postgresql")


class SessionSummary(Base, UUIDMixin, TimestampMixin):
    """Narrative summary + key topics for one past chat session.

    One row per session (UNIQUE on session_id); re-summarizing upserts the
    existing row so the episodic layer stays bounded.
    """

    __tablename__ = "session_summaries"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
    )
    summary: Mapped[str] = mapped_column(Text)
    key_topics: Mapped[list[str]] = mapped_column(_JSONField, default=list)

    __table_args__ = (
        UniqueConstraint("session_id", name="uq_session_summaries_session_id"),
    )
