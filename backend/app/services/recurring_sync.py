"""Recurring transaction sync — port of lib/db/recurringSync.ts."""

import asyncio
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.account import Account
from app.models.recurring import RecurringTransaction
from app.models.transaction import Transaction

logger = get_logger(__name__)

_lock = asyncio.Lock()

MAX_RUNS_PER_ITEM = 50


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def _fmt(d: date) -> str:
    return d.isoformat()


def _next_date(current: date, frequency: str) -> date:
    if frequency == "daily":
        return current + timedelta(days=1)
    if frequency == "weekly":
        return current + timedelta(weeks=1)
    if frequency == "monthly":
        return current + relativedelta(months=1)
    if frequency == "yearly":
        return current + relativedelta(years=1)
    return current + timedelta(days=1)


def _next_allowed_day(from_date: date, allowed: list[int]) -> date:
    """Find next date >= from_date that falls on one of the allowed weekdays (0=Mon…6=Sun).

    Note: JS uses 0=Sun…6=Sat, Python uses 0=Mon…6=Sun.
    We convert JS day numbers on read.
    """
    for i in range(7):
        d = from_date + timedelta(days=i)
        if d.weekday() in allowed:
            return d
    return from_date


def _js_days_to_python(js_days: list[int]) -> list[int]:
    """Convert JS weekday numbers (0=Sun) to Python (0=Mon)."""
    return [(d - 1) % 7 for d in js_days]


async def _adjust_balance(db: AsyncSession, account_id, delta: float) -> None:
    await db.execute(
        update(Account)
        .where(Account.id == account_id)
        .values(balance=Account.balance + delta)
    )


async def _create_transaction(
    db: AsyncSession, item: RecurringTransaction, date_str: str
) -> None:
    tx = Transaction(
        type=item.type,
        amount=item.amount,
        account_id=item.account_id,
        to_account_id=item.to_account_id,
        category_id=item.category_id,
        description=item.description,
        date=date_str,
        note="Giao dịch tự động định kỳ",
    )
    db.add(tx)

    tx_type = item.type if isinstance(item.type, str) else item.type.value
    if tx_type == "income":
        await _adjust_balance(db, item.account_id, item.amount)
    elif tx_type == "expense":
        await _adjust_balance(db, item.account_id, -item.amount)
    elif tx_type == "transfer" and item.to_account_id:
        await _adjust_balance(db, item.account_id, -item.amount)
        await _adjust_balance(db, item.to_account_id, item.amount)


async def process_recurring(db: AsyncSession) -> None:
    """Process all due recurring transactions. Guarded by async lock."""
    if _lock.locked():
        return

    async with _lock:
        await _process(db)


async def _process(db: AsyncSession) -> None:
    today_str = _fmt(date.today())

    result = await db.execute(
        select(RecurringTransaction).where(RecurringTransaction.is_active.is_(True))
    )
    items = list(result.scalars().all())

    due = [i for i in items if i.next_run_date and i.next_run_date <= today_str]
    if not due:
        return

    logger.info("Recurring sync: %d items due", len(due))

    for item in due:
        now_str = date.today().isoformat()

        if item.days_of_week:
            allowed = _js_days_to_python(item.days_of_week)
            if not allowed:
                continue

            current = _next_allowed_day(_parse_date(item.next_run_date), allowed)
            runs = 0

            while _fmt(current) <= today_str and runs < MAX_RUNS_PER_ITEM:
                runs += 1
                await _create_transaction(db, item, _fmt(current))
                current = _next_allowed_day(current + timedelta(days=1), allowed)

            item.next_run_date = _fmt(current)
            item.last_run_date = now_str
            continue

        # Normal frequency mode
        current_str = item.next_run_date
        runs = 0
        freq = item.frequency if isinstance(item.frequency, str) else item.frequency.value

        while current_str <= today_str and runs < MAX_RUNS_PER_ITEM:
            runs += 1
            await _create_transaction(db, item, current_str)
            current_str = _fmt(_next_date(_parse_date(current_str), freq))

        item.next_run_date = current_str
        item.last_run_date = now_str

    await db.flush()
    logger.info("Recurring sync complete")
