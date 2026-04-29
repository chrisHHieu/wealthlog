"""Account request/response schemas."""

from pydantic import Field

from app.models.account import AccountType
from app.schemas.base import CamelModel, TimestampResponse


class AccountCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: AccountType = AccountType.CASH
    balance: float = 0
    currency: str = Field(default="VND", max_length=10)
    color: str = Field(default="#00C896", max_length=20)
    icon: str = Field(default="💳", max_length=10)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class AccountUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: AccountType | None = None
    balance: float | None = None
    currency: str | None = Field(default=None, max_length=10)
    color: str | None = Field(default=None, max_length=20)
    icon: str | None = Field(default=None, max_length=10)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class AccountResponse(TimestampResponse):
    name: str
    type: AccountType
    balance: float
    currency: str
    color: str
    icon: str
    description: str | None
    is_active: bool
