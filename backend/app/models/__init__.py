"""SQLAlchemy models — import all models here so Alembic can discover them."""

from app.models.account import Account, AccountType
from app.models.budget import Budget
from app.models.category import BudgetGroup, Category, CategoryType
from app.models.chat import ChatMessage, ChatSession
from app.models.goal import Goal, GoalContribution, GoalType
from app.models.investment import Investment, InvestmentType
from app.models.recurring import Frequency, RecurringTransaction
from app.models.session_summary import SessionSummary
from app.models.setting import Setting
from app.models.transaction import Transaction, TransactionType
from app.models.user_fact import UserFact

__all__ = [
    "Account",
    "AccountType",
    "Budget",
    "BudgetGroup",
    "Category",
    "CategoryType",
    "ChatMessage",
    "ChatSession",
    "Frequency",
    "Goal",
    "GoalContribution",
    "GoalType",
    "Investment",
    "InvestmentType",
    "RecurringTransaction",
    "SessionSummary",
    "Setting",
    "Transaction",
    "TransactionType",
    "UserFact",
]
