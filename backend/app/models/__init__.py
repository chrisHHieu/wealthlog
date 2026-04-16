"""SQLAlchemy models — import all models here so Alembic can discover them."""

from app.models.account import Account, AccountType
from app.models.budget import Budget
from app.models.category import BudgetGroup, Category, CategoryType
from app.models.goal import Goal, GoalContribution, GoalType
from app.models.investment import Investment, InvestmentType
from app.models.recurring import Frequency, RecurringTransaction
from app.models.setting import Setting
from app.models.transaction import Transaction, TransactionType

__all__ = [
    "Account",
    "AccountType",
    "Budget",
    "BudgetGroup",
    "Category",
    "CategoryType",
    "Frequency",
    "Goal",
    "GoalContribution",
    "GoalType",
    "Investment",
    "InvestmentType",
    "RecurringTransaction",
    "Setting",
    "Transaction",
    "TransactionType",
]
