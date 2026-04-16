import enum

from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class AccountType(str, enum.Enum):
    CASH = "cash"
    BANK = "bank"
    EWALLET = "ewallet"
    INVESTMENT = "investment"
    SAVINGS = "savings"
    DEBT = "debt"


class Account(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "accounts"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AccountType] = mapped_column(nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="VND")
    color: Mapped[str] = mapped_column(String(20), default="#00C896")
    icon: Mapped[str] = mapped_column(String(10), default="💳")
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        back_populates="account",
        foreign_keys="Transaction.account_id",
        cascade="all, delete-orphan",
    )
    investments: Mapped[list["Investment"]] = relationship(  # noqa: F821
        back_populates="account",
    )

    def __repr__(self) -> str:
        return f"<Account {self.name} ({self.type.value})>"
