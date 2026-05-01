"""UserModel — versioned Sonnet-synthesized understanding of the user."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class UserModel(Base, UUIDMixin):
    """Periodic synthesis of all facts + session history into a coherent user profile.

    Multiple versions are kept (newest N). Always query with
    ``ORDER BY created_at DESC LIMIT 1`` to get the current model.
    """

    __tablename__ = "user_models"

    content: Mapped[str] = mapped_column(Text)
    # How many summarized sessions were included at synthesis time — used to
    # decide whether enough new sessions have arrived to warrant re-synthesis.
    session_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
