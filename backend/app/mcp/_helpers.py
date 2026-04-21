"""Shared helpers for MCP transaction tools."""

from calendar import monthrange
from datetime import date
from uuid import UUID

from sqlalchemy import and_, select, update

from app.models.account import Account
from app.models.category import Category


def current_month() -> str:
    d = date.today()
    return f"{d.year}-{d.month:02d}"


def today() -> str:
    return date.today().isoformat()


def month_range(month: str) -> tuple[str, str]:
    """Return (start, end) ISO date strings for a YYYY-MM month.

    End is the actual last day (28/29/30/31) — avoids the ``{m}-31`` hack
    that would break if ``transactions.date`` ever migrates from String to
    a real DATE column.
    """
    y, m = int(month[:4]), int(month[5:7])
    last = monthrange(y, m)[1]
    return f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last:02d}"


async def adjust_balance(db, account_id: UUID, delta: float) -> None:
    await db.execute(
        update(Account)
        .where(Account.id == account_id)
        .values(balance=Account.balance + delta)
    )


async def apply_balance(
    db, tx_type: str, amount: float,
    account_id: UUID, to_account_id: UUID | None,
) -> None:
    if tx_type == "income":
        await adjust_balance(db, account_id, amount)
    elif tx_type == "expense":
        await adjust_balance(db, account_id, -amount)
    elif tx_type == "transfer" and to_account_id:
        await adjust_balance(db, account_id, -amount)
        await adjust_balance(db, to_account_id, amount)


async def reverse_balance(
    db, tx_type: str, amount: float,
    account_id: UUID, to_account_id: UUID | None,
) -> None:
    if tx_type == "income":
        await adjust_balance(db, account_id, -amount)
    elif tx_type == "expense":
        await adjust_balance(db, account_id, amount)
    elif tx_type == "transfer" and to_account_id:
        await adjust_balance(db, account_id, amount)
        await adjust_balance(db, to_account_id, -amount)


async def resolve_category(db, category_name: str) -> UUID | None:
    """Tìm category theo tên (case-insensitive). Trả về ID hoặc None."""
    return (
        await db.execute(
            select(Category.id).where(Category.name.ilike(category_name)).limit(1)
        )
    ).scalar()


async def resolve_account(db, account_name: str) -> UUID | None:
    """Tìm account theo tên (case-insensitive). Trả về ID hoặc None."""
    return (
        await db.execute(
            select(Account.id).where(
                and_(Account.name.ilike(account_name), Account.is_active.is_(True))
            ).limit(1)
        )
    ).scalar()


async def get_default_account(db) -> UUID | None:
    """Lấy tài khoản active đầu tiên làm default."""
    return (
        await db.execute(
            select(Account.id)
            .where(Account.is_active.is_(True))
            .order_by(Account.created_at)
            .limit(1)
        )
    ).scalar()
