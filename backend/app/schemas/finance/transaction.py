"""Transaction request/response schemas."""

import uuid

from pydantic import Field

from app.models.transaction import TransactionType
from app.schemas.base import CamelModel, PaginatedResponse, TimestampResponse


class TransactionCreate(CamelModel):
    type: TransactionType
    amount: float = Field(..., gt=0)
    account_id: uuid.UUID
    to_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    description: str = Field(default="", max_length=500)
    note: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class TransactionUpdate(CamelModel):
    type: TransactionType | None = None
    amount: float | None = Field(default=None, gt=0)
    account_id: uuid.UUID | None = None
    to_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class TransactionResponse(TimestampResponse):
    """Full transaction with joined account/category names for FE display."""

    type: TransactionType
    amount: float
    account_id: uuid.UUID
    to_account_id: uuid.UUID | None
    category_id: uuid.UUID | None
    description: str
    note: str | None
    tags: list[str] | None
    date: str

    # Joined fields (populated by router, not from ORM directly)
    account_name: str | None = None
    account_icon: str | None = None
    category_name: str | None = None
    category_icon: str | None = None
    category_color: str | None = None


TransactionListResponse = PaginatedResponse[TransactionResponse]
