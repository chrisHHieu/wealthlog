"""Investments CRUD router."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.investment import Investment
from app.schemas.investment import InvestmentCreate, InvestmentResponse, InvestmentUpdate

logger = get_logger(__name__)
router = APIRouter(prefix="/api/investments", tags=["investments"])


@router.get("", response_model=list[InvestmentResponse])
async def list_investments(db: AsyncSession = Depends(get_db)) -> list[Investment]:
    result = await db.execute(select(Investment).order_by(Investment.buy_date))
    return list(result.scalars().all())


@router.post("", response_model=InvestmentResponse, status_code=201)
async def create_investment(
    body: InvestmentCreate,
    db: AsyncSession = Depends(get_db),
) -> Investment:
    inv = Investment(**body.model_dump())
    db.add(inv)
    await db.flush()
    logger.info("Created investment '%s' (%s)", inv.name, inv.type.value)
    return inv


@router.put("/{investment_id}", response_model=InvestmentResponse)
async def update_investment(
    investment_id: uuid.UUID,
    body: InvestmentUpdate,
    db: AsyncSession = Depends(get_db),
) -> Investment:
    inv = await db.get(Investment, investment_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investment not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(inv, field, value)
    await db.flush()
    await db.refresh(inv)
    logger.info("Updated investment %s", investment_id)
    return inv


@router.delete("/{investment_id}")
async def delete_investment(
    investment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    inv = await db.get(Investment, investment_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investment not found")
    await db.delete(inv)
    await db.flush()
    logger.info("Deleted investment %s", investment_id)
    return {"success": True}
