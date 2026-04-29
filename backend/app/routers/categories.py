"""Categories CRUD router with used_only filter."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.finance.category import CategoryCreate, CategoryResponse, CategoryUpdate

logger = get_logger(__name__)
router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    used_only: bool = Query(False, alias="usedOnly"),
    start_date: str | None = Query(None, alias="startDate"),
    end_date: str | None = Query(None, alias="endDate"),
    db: AsyncSession = Depends(get_db),
) -> list[Category]:
    if used_only:
        # Get distinct category IDs from transactions in date range
        stmt = select(Transaction.category_id).distinct()
        if start_date:
            stmt = stmt.where(Transaction.date >= start_date)
        if end_date:
            stmt = stmt.where(Transaction.date <= end_date)
        result = await db.execute(stmt)
        used_ids = [row for row in result.scalars().all() if row is not None]
        if not used_ids:
            return []
        cats = await db.execute(
            select(Category)
            .where(Category.id.in_(used_ids))
            .order_by(Category.name)
        )
        return list(cats.scalars().all())

    result = await db.execute(select(Category).order_by(Category.name))
    return list(result.scalars().all())


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
) -> Category:
    category = Category(**body.model_dump())
    db.add(category)
    await db.flush()
    logger.info("Created category %s", category.name)
    return category


@router.put("", response_model=CategoryResponse)
async def update_category(
    body: CategoryUpdate,
    category_id: uuid.UUID = Query(..., alias="id"),
    db: AsyncSession = Depends(get_db),
) -> Category:
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.flush()
    logger.info("Updated category %s", category_id)
    return category


@router.delete("")
async def delete_category(
    category_id: uuid.UUID = Query(..., alias="id"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(category)
    await db.flush()
    logger.info("Deleted category %s", category_id)
    return {"success": True}
