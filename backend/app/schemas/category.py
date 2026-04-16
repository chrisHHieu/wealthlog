"""Category request/response schemas."""

from pydantic import Field

from app.models.category import BudgetGroup, CategoryType
from app.schemas.base import CamelModel, CreatedAtResponse


class CategoryCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: CategoryType = CategoryType.EXPENSE
    budget_group: BudgetGroup | None = None
    icon: str = Field(default="📦", max_length=10)
    color: str = Field(default="#6366f1", max_length=20)
    is_default: bool = False


class CategoryUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: CategoryType | None = None
    budget_group: BudgetGroup | None = None
    icon: str | None = Field(default=None, max_length=10)
    color: str | None = Field(default=None, max_length=20)
    is_default: bool | None = None


class CategoryResponse(CreatedAtResponse):
    name: str
    type: CategoryType
    budget_group: BudgetGroup | None
    icon: str
    color: str
    is_default: bool
