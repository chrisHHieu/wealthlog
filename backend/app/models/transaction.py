import enum
import uuid

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class Transaction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_date", "date"),
        Index("ix_transactions_account_id", "account_id"),
        Index("ix_transactions_category_id", "category_id"),
        Index("ix_transactions_type", "type"),
    )

    type: Mapped[TransactionType] = mapped_column(nullable=False)
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
    note: Mapped[str | None] = mapped_column(String(1000))
    tags: Mapped[list | None] = mapped_column(JSON)
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # ISO date YYYY-MM-DD

    # Relationships
    account: Mapped["Account"] = relationship(  # noqa: F821
        back_populates="transactions",
        foreign_keys=[account_id],
    )
    to_account: Mapped["Account | None"] = relationship(  # noqa: F821
        foreign_keys=[to_account_id],
    )
    category: Mapped["Category | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<Transaction {self.type.value} {self.amount} on {self.date}>"
