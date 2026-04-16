"""Recurring transaction request/response schemas."""

import uuid

from pydantic import Field

from app.models.recurring import Frequency
from app.schemas.base import CamelModel, CreatedAtResponse


class RecurringCreate(CamelModel):
    type: str = Field(..., max_length=20)  # income/expense/transfer
    amount: float = Field(..., gt=0)
    account_id: uuid.UUID
    to_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    description: str = Field(default="", max_length=500)
    frequency: Frequency
    days_of_week: list[int] | None = None
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    next_run_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    is_active: bool = True


class RecurringUpdate(CamelModel):
    type: str | None = Field(default=None, max_length=20)
    amount: float | None = Field(default=None, gt=0)
    account_id: uuid.UUID | None = None
    to_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=500)
    frequency: Frequency | None = None
    days_of_week: list[int] | None = None
    start_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    next_run_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    is_active: bool | None = None


class RecurringResponse(CreatedAtResponse):
    """Full recurring transaction with joined names."""

    type: str
    amount: float
    account_id: uuid.UUID
    to_account_id: uuid.UUID | None
    category_id: uuid.UUID | None
    description: str
    frequency: Frequency
    days_of_week: list[int] | None
    start_date: str
    next_run_date: str
    last_run_date: str | None
    is_active: bool

    # Joined fields
    account_name: str | None = None
    category_name: str | None = None
    category_icon: str | None = None
    category_color: str | None = None
