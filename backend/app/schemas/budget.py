"""Budget request/response schemas."""

import uuid

from pydantic import Field

from app.schemas.base import CamelModel, CreatedAtResponse


class BudgetCreate(CamelModel):
    category_id: uuid.UUID
    amount: float = Field(..., gt=0)
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")


class BudgetUpdate(CamelModel):
    amount: float | None = Field(default=None, gt=0)


class BudgetResponse(CreatedAtResponse):
    """Budget with joined category info."""

    category_id: uuid.UUID
    amount: float
    month: str

    # Joined fields
    category_name: str | None = None
    category_icon: str | None = None
    category_color: str | None = None


class BudgetCheckResponse(CamelModel):
    """Budget vs actual spending comparison."""

    budget_amount: float
    total_spent: float
    percent: float
    remaining: float
    is_exceeded: bool
    is_warning: bool
