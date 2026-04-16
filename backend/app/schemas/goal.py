"""Goal request/response schemas."""

import uuid
from datetime import datetime

from pydantic import Field

from app.models.goal import GoalType
from app.schemas.base import CamelModel, CreatedAtResponse, TimestampResponse


class GoalCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: GoalType = GoalType.CUSTOM
    target_amount: float = Field(..., gt=0)
    current_amount: float = Field(default=0, ge=0)
    deadline: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    icon: str = Field(default="🎯", max_length=10)
    color: str = Field(default="#00C896", max_length=20)
    description: str | None = Field(default=None, max_length=500)


class GoalUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: GoalType | None = None
    target_amount: float | None = Field(default=None, gt=0)
    current_amount: float | None = Field(default=None, ge=0)
    deadline: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    icon: str | None = Field(default=None, max_length=10)
    color: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=500)
    is_completed: bool | None = None


class GoalAddAmount(CamelModel):
    """Request body for adding a contribution to a goal."""

    amount: float = Field(..., gt=0)
    note: str | None = Field(default=None, max_length=500)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class GoalContributionResponse(CreatedAtResponse):
    goal_id: uuid.UUID
    amount: float
    note: str | None
    date: str


class GoalResponse(TimestampResponse):
    name: str
    type: GoalType
    target_amount: float
    current_amount: float
    deadline: str | None
    icon: str
    color: str
    description: str | None
    is_completed: bool
    contributions: list[GoalContributionResponse] = []
