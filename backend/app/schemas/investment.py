"""Investment request/response schemas."""

import uuid

from pydantic import Field

from app.models.investment import InvestmentType
from app.schemas.base import CamelModel, TimestampResponse


class InvestmentCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: InvestmentType = InvestmentType.STOCK
    symbol: str | None = Field(default=None, max_length=20)
    quantity: float = Field(default=0, ge=0)
    buy_price: float = Field(..., ge=0)
    current_price: float = Field(..., ge=0)
    buy_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    account_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=1000)


class InvestmentUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: InvestmentType | None = None
    symbol: str | None = Field(default=None, max_length=20)
    quantity: float | None = Field(default=None, ge=0)
    buy_price: float | None = Field(default=None, ge=0)
    current_price: float | None = Field(default=None, ge=0)
    buy_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    account_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=1000)


class InvestmentResponse(TimestampResponse):
    name: str
    type: InvestmentType
    symbol: str | None
    quantity: float
    buy_price: float
    current_price: float
    buy_date: str
    account_id: uuid.UUID | None
    note: str | None
