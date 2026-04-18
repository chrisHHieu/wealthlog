"""User facts — long-term memory extracted from conversations."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class UserFact(Base, UUIDMixin):
    """A piece of long-term knowledge about the user, persisted across sessions."""

    __tablename__ = "user_facts"

    fact: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(
        String(50), default="general",
    )  # preference, habit, goal, context
    source_session_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
    )  # which session it was extracted from
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
