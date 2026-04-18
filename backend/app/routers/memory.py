"""User facts (long-term memory) management endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user_fact import UserFact
from app.schemas.base import CamelModel

router = APIRouter(prefix="/api/memory", tags=["memory"])


class FactResponse(CamelModel):
    id: uuid.UUID
    fact: str
    category: str
    created_at: str
    updated_at: str


class FactCreate(CamelModel):
    fact: str
    category: str = "general"


@router.get("/facts", response_model=list[FactResponse])
async def list_facts(db: AsyncSession = Depends(get_db)):
    """List all user facts."""
    rows = (
        await db.execute(
            select(UserFact).order_by(UserFact.updated_at.desc())
        )
    ).scalars().all()

    return [
        FactResponse(
            id=r.id,
            fact=r.fact,
            category=r.category,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in rows
    ]


@router.post("/facts", response_model=FactResponse)
async def create_fact(
    body: FactCreate,
    db: AsyncSession = Depends(get_db),
):
    """Manually add a user fact."""
    fact = UserFact(fact=body.fact, category=body.category)
    db.add(fact)
    await db.flush()
    return FactResponse(
        id=fact.id,
        fact=fact.fact,
        category=fact.category,
        created_at=fact.created_at.isoformat(),
        updated_at=fact.updated_at.isoformat(),
    )


@router.delete("/facts/{fact_id}")
async def delete_fact(
    fact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a user fact."""
    result = await db.execute(
        select(UserFact).where(UserFact.id == fact_id)
    )
    fact = result.scalar_one_or_none()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    await db.delete(fact)
    return {"ok": True}
