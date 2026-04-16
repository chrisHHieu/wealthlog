import enum

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import CreatedAtMixin, UUIDMixin


class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    BOTH = "both"


class BudgetGroup(str, enum.Enum):
    NEEDS = "needs"
    WANTS = "wants"
    SAVINGS = "savings"


class Category(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[CategoryType] = mapped_column(default=CategoryType.EXPENSE)
    budget_group: Mapped[BudgetGroup | None] = mapped_column()
    icon: Mapped[str] = mapped_column(String(10), default="📦")
    color: Mapped[str] = mapped_column(String(20), default="#6366f1")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<Category {self.name} ({self.type.value})>"
