"""Recurring transactions CRUD router."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.account import Account
from app.models.category import Category
from app.models.recurring import RecurringTransaction
from app.schemas.recurring import RecurringCreate, RecurringResponse, RecurringUpdate
from app.services.recurring_sync import process_recurring

logger = get_logger(__name__)
router = APIRouter(prefix="/api/recurring", tags=["recurring"])


@router.get("", response_model=list[RecurringResponse])
async def list_recurring(db: AsyncSession = Depends(get_db)):
    await process_recurring(db)
    stmt = (
        select(
            RecurringTransaction,
            Account.name.label("account_name"),
            Category.name.label("category_name"),
            Category.icon.label("category_icon"),
            Category.color.label("category_color"),
        )
        .outerjoin(Account, RecurringTransaction.account_id == Account.id)
        .outerjoin(Category, RecurringTransaction.category_id == Category.id)
        .order_by(RecurringTransaction.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    return [
        {
            **{c.key: getattr(row[0], c.key) for c in row[0].__table__.columns},
            "account_name": row[1],
            "category_name": row[2],
            "category_icon": row[3],
            "category_color": row[4],
        }
        for row in rows
    ]


@router.post("", response_model=RecurringResponse, status_code=201)
async def create_recurring(
    body: RecurringCreate,
    db: AsyncSession = Depends(get_db),
) -> RecurringTransaction:
    item = RecurringTransaction(**body.model_dump())
    db.add(item)
    await db.flush()
    logger.info("Created recurring '%s' (%s)", item.description, item.frequency.value)
    return item


@router.put("/{item_id}", response_model=RecurringResponse)
async def update_recurring(
    item_id: uuid.UUID,
    body: RecurringUpdate,
    db: AsyncSession = Depends(get_db),
) -> RecurringTransaction:
    item = await db.get(RecurringTransaction, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.flush()
    logger.info("Updated recurring %s", item_id)
    return item


@router.patch("/{item_id}", response_model=RecurringResponse)
async def patch_recurring(
    item_id: uuid.UUID,
    body: RecurringUpdate,
    db: AsyncSession = Depends(get_db),
) -> RecurringTransaction:
    item = await db.get(RecurringTransaction, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.flush()
    logger.info("Patched recurring %s", item_id)
    return item


@router.delete("/{item_id}")
async def delete_recurring(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    item = await db.get(RecurringTransaction, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    await db.delete(item)
    await db.flush()
    logger.info("Deleted recurring %s", item_id)
    return {"success": True}
