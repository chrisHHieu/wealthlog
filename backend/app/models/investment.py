import enum
import uuid

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class InvestmentType(str, enum.Enum):
    STOCK = "stock"
    ETF = "etf"
    GOLD = "gold"
    REALESTATE = "realestate"
    SAVINGS = "savings"
    CRYPTO = "crypto"
    OTHER = "other"


class Investment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "investments"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[InvestmentType] = mapped_column(default=InvestmentType.STOCK)
    symbol: Mapped[str | None] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Float, default=0)
    buy_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    buy_date: Mapped[str] = mapped_column(String(10), nullable=False)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id"),
    )
    note: Mapped[str | None] = mapped_column(String(1000))

    # Relationships
    account: Mapped["Account | None"] = relationship(  # noqa: F821
        back_populates="investments",
    )

    def __repr__(self) -> str:
        return f"<Investment {self.name} ({self.type.value})>"
