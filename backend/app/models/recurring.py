import enum
import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import CreatedAtMixin, UUIDMixin


class Frequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurringTransaction(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "recurring_transactions"

    type: Mapped[str] = mapped_column(String(20), nullable=False)  # income/expense/transfer
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id"),
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id"),
    )
    description: Mapped[str] = mapped_column(String(500), default="")
    frequency: Mapped[Frequency] = mapped_column(nullable=False)
    days_of_week: Mapped[list | None] = mapped_column(JSON)  # e.g. [1,2,3,4]
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)
    next_run_date: Mapped[str] = mapped_column(String(10), nullable=False)
    last_run_date: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    account: Mapped["Account"] = relationship(  # noqa: F821
        foreign_keys=[account_id],
    )
    to_account: Mapped["Account | None"] = relationship(  # noqa: F821
        foreign_keys=[to_account_id],
    )
    category: Mapped["Category | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<Recurring {self.description} ({self.frequency.value})>"
