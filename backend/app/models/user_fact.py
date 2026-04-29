"""User facts — long-term memory extracted from conversations."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
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
    # NULL = evergreen. Non-null = time-bound fact (e.g. "đang là sinh viên"),
    # filtered out of retrieval once passed.
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # 1-10 scale. Higher = more important. Drives prompt ordering so the most
    # impactful facts survive when the injection budget is tight.
    importance: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    # True only after the user explicitly confirms the fact via the memory MCP
    # tools. Ranked above unverified facts at equal importance so confirmed
    # information beats guesses for finance-critical numbers (goals, balances).
    verified_by_user: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
    )
    # Reviewer's self-assessed certainty (1-10). Independent of importance:
    # a low-confidence guess can still be high-importance ("user might be
    # saving for a house"). Internal-only — not surfaced in the prompt block.
    confidence: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    # Usage stats — let frequently-surfaced facts bubble up among equals.
    access_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
