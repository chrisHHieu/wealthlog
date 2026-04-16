"""Seed default categories and settings — port of lib/db/seed.ts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.category import Category
from app.models.setting import Setting

logger = get_logger(__name__)

DEFAULT_CATEGORIES = [
    # Thu nhập
    {"name": "Lương", "type": "income", "icon": "💰", "color": "#00C896", "is_default": True},
    {"name": "Thưởng", "type": "income", "icon": "🎁", "color": "#10b981", "is_default": True},
    {"name": "Đầu tư sinh lời", "type": "income", "icon": "📈", "color": "#0ea5e9", "is_default": True, "budget_group": "savings"},
    {"name": "Thu nhập phụ", "type": "income", "icon": "💵", "color": "#8b5cf6", "is_default": True},
    {"name": "Cho vay thu về", "type": "income", "icon": "🔄", "color": "#06b6d4", "is_default": True, "budget_group": "savings"},
    # Chi tiêu — Thiết yếu (Needs)
    {"name": "Ăn uống", "type": "expense", "icon": "🍜", "color": "#f59e0b", "is_default": True, "budget_group": "needs"},
    {"name": "Di chuyển", "type": "expense", "icon": "🚗", "color": "#ef4444", "is_default": True, "budget_group": "needs"},
    {"name": "Sức khỏe", "type": "expense", "icon": "🏥", "color": "#f43f5e", "is_default": True, "budget_group": "needs"},
    {"name": "Nhà ở", "type": "expense", "icon": "🏠", "color": "#14b8a6", "is_default": True, "budget_group": "needs"},
    {"name": "Hóa đơn & Tiện ích", "type": "expense", "icon": "⚡", "color": "#f97316", "is_default": True, "budget_group": "needs"},
    {"name": "Gia đình", "type": "expense", "icon": "👨\u200d👩\u200d👧", "color": "#84cc16", "is_default": True, "budget_group": "needs"},
    {"name": "Phí ngân hàng", "type": "expense", "icon": "🏦", "color": "#6b7280", "is_default": True, "budget_group": "needs"},
    # Chi tiêu — Mong muốn (Wants)
    {"name": "Mua sắm", "type": "expense", "icon": "🛍️", "color": "#ec4899", "is_default": True, "budget_group": "wants"},
    {"name": "Giải trí", "type": "expense", "icon": "🎬", "color": "#8b5cf6", "is_default": True, "budget_group": "wants"},
    {"name": "Giáo dục", "type": "expense", "icon": "📚", "color": "#3b82f6", "is_default": True, "budget_group": "wants"},
    {"name": "Làm đẹp", "type": "expense", "icon": "💄", "color": "#d946ef", "is_default": True, "budget_group": "wants"},
    {"name": "Du lịch", "type": "expense", "icon": "✈️", "color": "#06b6d4", "is_default": True, "budget_group": "wants"},
    # Khác
    {"name": "Khác", "type": "both", "icon": "📦", "color": "#9ca3af", "is_default": True, "budget_group": "wants"},
]

DEFAULT_SETTINGS = [
    {"key": "userName", "value": "Nguyễn Hoàng Hiếu"},
    {"key": "currency", "value": "VND"},
    {"key": "theme", "value": "dark"},
    {"key": "language", "value": "vi"},
]


async def seed(db: AsyncSession) -> None:
    """Insert default categories + settings if DB is empty."""
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
