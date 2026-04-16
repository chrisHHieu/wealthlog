"""Pydantic v2 schemas — central registry."""

from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.schemas.budget import (
    BudgetCheckResponse,
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
)
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.dashboard import DashboardResponse
from app.schemas.goal import (
    GoalAddAmount,
    GoalContributionResponse,
    GoalCreate,
    GoalResponse,
    GoalUpdate,
)
from app.schemas.investment import (
    InvestmentCreate,
    InvestmentResponse,
    InvestmentUpdate,
)
from app.schemas.recurring import RecurringCreate, RecurringResponse, RecurringUpdate
from app.schemas.reports import ReportsResponse
from app.schemas.setting import SettingsResponse, SettingsUpdate
from app.schemas.transaction import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)

__all__ = [
    "AccountCreate",
    "AccountResponse",
    "AccountUpdate",
    "BudgetCheckResponse",
    "BudgetCreate",
    "BudgetResponse",
    "BudgetUpdate",
    "CategoryCreate",
    "CategoryResponse",
    "CategoryUpdate",
    "DashboardResponse",
    "GoalAddAmount",
    "GoalContributionResponse",
    "GoalCreate",
    "GoalResponse",
    "GoalUpdate",
    "InvestmentCreate",
    "InvestmentResponse",
    "InvestmentUpdate",
    "RecurringCreate",
    "RecurringResponse",
    "RecurringUpdate",
    "ReportsResponse",
    "SettingsResponse",
    "SettingsUpdate",
    "TransactionCreate",
    "TransactionListResponse",
    "TransactionResponse",
    "TransactionUpdate",
]
