"""Per-run token-usage ledger for the AI agent.

One row per agent run (per chat request), recording the token counts and the
computed USD cost. This is the audit trail that answers "where did the LLM bill
go?" — sliceable by session, model, and time. Cost is Numeric, never float:
money math through binary floats accumulates rounding error.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class TokenUsage(Base, UUIDMixin):
    """Token counts + cost for a single agent run."""

    __tablename__ = "token_usage"

    # Nullable: a run may be metered before/without a persisted session.
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True,
    )
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(default=0)
    cache_write_tokens: Mapped[int] = mapped_column(default=0)
    cache_read_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal(0))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_token_usage_session_id", "session_id"),
        Index("ix_token_usage_created_at", "created_at"),
    )
