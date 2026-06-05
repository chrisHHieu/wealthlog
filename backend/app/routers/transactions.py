"""Transactions CRUD router with balance logic and pagination."""

import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_errors import not_found, validation_error
from app.database import get_db
from app.domain.balance import apply_balance, reverse_balance
from app.logging_config import get_logger
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.schemas.finance.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.recurring_sync import process_recurring

logger = get_logger(__name__)
router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _type_value(tx_type: TransactionType | str) -> str:
    return tx_type.value if hasattr(tx_type, "value") else str(tx_type)


def _validate_balance_contract(
    tx_type: TransactionType | str,
    account_id: uuid.UUID,
    to_account_id: uuid.UUID | None,
) -> None:
    type_value = _type_value(tx_type)
    if type_value == "transfer":
        if to_account_id is None:
            raise validation_error("Transfer requires toAccountId")
        if to_account_id == account_id:
            raise validation_error("Transfer source and destination accounts must be different")
        return

    if to_account_id is not None:
        raise validation_error("toAccountId is only allowed for transfer transactions")


def _build_filters(
    start_date: str | None,
    end_date: str | None,
    account_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    type_: str | None,
    search: str | None,
) -> list:
    conditions = []
    if start_date:
        conditions.append(Transaction.date >= start_date)
    if end_date:
        conditions.append(Transaction.date <= end_date)
    if account_id:
        conditions.append(Transaction.account_id == account_id)
    if category_id:
        conditions.append(Transaction.category_id == category_id)
    if type_:
        conditions.append(Transaction.type == type_)
    if search:
        conditions.append(Transaction.description.ilike(f"%{search}%"))
    return conditions


def _to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _to_response(row) -> dict:
    tx = row[0] if hasattr(row[0], "id") else row
    result = {_to_camel(c.key): getattr(tx, c.key) for c in tx.__table__.columns}
    result["accountName"] = row[1] if len(row) > 1 else None
    result["accountIcon"] = row[2] if len(row) > 2 else None
    result["categoryName"] = row[3] if len(row) > 3 else None
    result["categoryIcon"] = row[4] if len(row) > 4 else None
    result["categoryColor"] = row[5] if len(row) > 5 else None
    return result


def _joined_query():
    return (
        select(
            Transaction,
            Account.name.label("account_name"),
            Account.icon.label("account_icon"),
            Category.name.label("category_name"),
            Category.icon.label("category_icon"),
            Category.color.label("category_color"),
        )
        .outerjoin(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
    )


@router.get("")
async def list_transactions(
    start_date: str | None = Query(None, alias="startDate"),
    end_date: str | None = Query(None, alias="endDate"),
    account_id: uuid.UUID | None = Query(None, alias="accountId"),
    category_id: uuid.UUID | None = Query(None, alias="categoryId"),
    type_: str | None = Query(None, alias="type"),
    search: str | None = None,
    page: int | None = None,
    page_size: int = Query(50, alias="pageSize"),
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    await process_recurring(db)
    conditions = _build_filters(start_date, end_date, account_id, category_id, type_, search)
    base = _joined_query()
    if conditions:
        base = base.where(*conditions)

    order = (Transaction.date.desc(), Transaction.created_at.desc())

    # Paginated mode
    if page is not None:
        page = max(1, page)
        count_q = select(func.count()).select_from(Transaction)
        if conditions:
            count_q = count_q.where(*conditions)
        total = (await db.execute(count_q)).scalar() or 0

        rows = (
            await db.execute(
                base.order_by(*order).limit(page_size).offset((page - 1) * page_size)
            )
        ).all()

        return {
            "data": [_to_response(r) for r in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": math.ceil(total / page_size) if page_size else 0,
        }

    # Legacy array mode
    rows = (await db.execute(base.order_by(*order).limit(limit))).all()
    return [_to_response(r) for r in rows]


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    body: TransactionCreate,
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    _validate_balance_contract(body.type, body.account_id, body.to_account_id)
    tx = Transaction(**body.model_dump())
    db.add(tx)
    await db.flush()

    await apply_balance(db, body.type.value, body.amount, body.account_id, body.to_account_id)
    logger.info("Created transaction %s %s %.2f", tx.type.value, tx.date, tx.amount)
    return tx


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    tx = await db.get(Transaction, transaction_id)
    if not tx:
        raise not_found("Transaction")
    return tx


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: uuid.UUID,
    body: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    tx = await db.get(Transaction, transaction_id)
    if not tx:
        raise not_found("Transaction")

    update_data = body.model_dump(exclude_unset=True)
    new_type = update_data.get("type", tx.type)
    new_account_id = update_data.get("account_id", tx.account_id)
    new_to_account_id = update_data.get("to_account_id", tx.to_account_id)
    if _type_value(new_type) != "transfer" and "to_account_id" not in update_data:
        new_to_account_id = None

    _validate_balance_contract(new_type, new_account_id, new_to_account_id)

    old_type = tx.type.value
    await reverse_balance(db, old_type, tx.amount, tx.account_id, tx.to_account_id)

    for field, value in update_data.items():
        setattr(tx, field, value)
    if _type_value(tx.type) != "transfer":
        tx.to_account_id = None
    await db.flush()

    await apply_balance(db, _type_value(tx.type), tx.amount, tx.account_id, tx.to_account_id)
    await db.refresh(tx)
    logger.info("Updated transaction %s", transaction_id)
    return tx


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    tx = await db.get(Transaction, transaction_id)
    if not tx:
        raise not_found("Transaction")

    await reverse_balance(db, tx.type.value, tx.amount, tx.account_id, tx.to_account_id)
    await db.delete(tx)
    await db.flush()
    logger.info("Deleted transaction %s", transaction_id)
    return {"success": True}
