"""WeeklyDigest — cached AI-generated financial health reports."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class WeeklyDigest(Base, UUIDMixin):
    """One digest report per generation run.

    Multiple rows accumulate over time — query by ``created_at DESC LIMIT 1``
    to get the latest. Kept as a log so users can compare week over week.
    """

    __tablename__ = "weekly_digests"

    content: Mapped[str] = mapped_column(Text)
    # YYYY-MM — which month's data this digest covers.
    generated_for_month: Mapped[str] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
