"""UserCommitment — things the user explicitly said they would do."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class UserCommitment(Base, UUIDMixin):
    """A commitment extracted from a session summary.

    Status lifecycle: pending → done | abandoned.
    Pending commitments surface in the agent's dynamic context so it can
    follow up naturally when the topic is relevant.
    """

    __tablename__ = "user_commitments"

    text: Mapped[str] = mapped_column(Text)
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Optional deadline extracted from the commitment text (e.g., "this week").
    due_by: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # pending | done | abandoned
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="'pending'")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
