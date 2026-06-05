"""Seed default categories and settings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.category import Category
from app.models.setting import Setting

logger = get_logger(__name__)

DEFAULT_CATEGORIES = [
    {"name": "Salary", "type": "income", "icon": "💰", "color": "#00C896", "is_default": True},
    {"name": "Bonus", "type": "income", "icon": "🎁", "color": "#10b981", "is_default": True},
    {
        "name": "Investment returns",
        "type": "income",
        "icon": "📈",
        "color": "#0ea5e9",
        "is_default": True,
        "budget_group": "savings",
    },
    {"name": "Side income", "type": "income", "icon": "💵", "color": "#8b5cf6", "is_default": True},
    {
        "name": "Loan repayment",
        "type": "income",
        "icon": "🔄",
        "color": "#06b6d4",
        "is_default": True,
        "budget_group": "savings",
    },
    {
        "name": "Food & Dining",
        "type": "expense",
        "icon": "🍜",
        "color": "#f59e0b",
        "is_default": True,
        "budget_group": "needs",
    },
    {
        "name": "Transportation",
        "type": "expense",
        "icon": "🚗",
        "color": "#ef4444",
        "is_default": True,
        "budget_group": "needs",
    },
    {
        "name": "Healthcare",
        "type": "expense",
        "icon": "🏥",
        "color": "#f43f5e",
        "is_default": True,
        "budget_group": "needs",
    },
    {
        "name": "Housing",
        "type": "expense",
        "icon": "🏠",
        "color": "#14b8a6",
        "is_default": True,
        "budget_group": "needs",
    },
    {
        "name": "Bills & Utilities",
        "type": "expense",
        "icon": "⚡",
        "color": "#f97316",
        "is_default": True,
        "budget_group": "needs",
    },
    {
        "name": "Family",
        "type": "expense",
        "icon": "👨‍👩‍👧",
        "color": "#84cc16",
        "is_default": True,
        "budget_group": "needs",
    },
    {
        "name": "Bank fees",
        "type": "expense",
        "icon": "🏦",
        "color": "#6b7280",
        "is_default": True,
        "budget_group": "needs",
    },
    {
        "name": "Shopping",
        "type": "expense",
        "icon": "🛍️",
        "color": "#ec4899",
        "is_default": True,
        "budget_group": "wants",
    },
    {
        "name": "Entertainment",
        "type": "expense",
        "icon": "🎬",
        "color": "#8b5cf6",
        "is_default": True,
        "budget_group": "wants",
    },
    {
        "name": "Education",
        "type": "expense",
        "icon": "📚",
        "color": "#3b82f6",
        "is_default": True,
        "budget_group": "wants",
    },
    {
        "name": "Beauty",
        "type": "expense",
        "icon": "💄",
        "color": "#d946ef",
        "is_default": True,
        "budget_group": "wants",
    },
    {
        "name": "Travel",
        "type": "expense",
        "icon": "✈️",
        "color": "#06b6d4",
        "is_default": True,
        "budget_group": "wants",
    },
    {"name": "Other", "type": "both", "icon": "📦", "color": "#9ca3af", "is_default": True, "budget_group": "wants"},
]

DEFAULT_SETTINGS = [
    {"key": "userName", "value": "Nguyen Hoang Hieu"},
    {"key": "currency", "value": "VND"},
    {"key": "theme", "value": "dark"},
    {"key": "language", "value": "en"},
]


async def seed(db: AsyncSession) -> None:
    """Insert default categories and settings if DB is empty."""
    existing = (await db.execute(select(Category).limit(1))).first()
    if existing:
        return

    logger.info("Seeding default categories and settings...")

    for cat_data in DEFAULT_CATEGORIES:
        db.add(Category(**cat_data))

    for setting_data in DEFAULT_SETTINGS:
        db.add(Setting(**setting_data))

    await db.flush()
    logger.info("Seed complete: %d categories, %d settings", len(DEFAULT_CATEGORIES), len(DEFAULT_SETTINGS))
