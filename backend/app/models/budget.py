import uuid

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import CreatedAtMixin, UUIDMixin


class Budget(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "budgets"

    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM

    # Relationships
    category: Mapped["Category"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<Budget {self.month} amount={self.amount}>"
