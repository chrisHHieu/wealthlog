"""User facts (long-term memory) management endpoints."""

import uuid
from datetime import datetime

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
    importance: int
    topics: list[str]
    verified_by_user: bool
    expires_at: datetime | None
    access_count: int
    last_accessed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FactCreate(CamelModel):
    fact: str
    category: str = "general"
    importance: int = 5
    topics: list[str] = []
    expires_at: datetime | None = None


class FactUpdate(CamelModel):
    fact: str
    category: str
    importance: int
    topics: list[str] = []
    verified_by_user: bool | None = None
    expires_at: datetime | None = None


def _to_response(r: UserFact) -> FactResponse:
    return FactResponse(
        id=r.id,
        fact=r.fact,
        category=r.category,
        importance=r.importance,
        topics=r.topics or [],
        verified_by_user=r.verified_by_user,
        expires_at=r.expires_at,
        access_count=r.access_count,
        last_accessed_at=r.last_accessed_at,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.get("/facts", response_model=list[FactResponse])
async def list_facts(db: AsyncSession = Depends(get_db)):
    """List all user facts ordered by importance then recency."""
    rows = (
        await db.execute(
            select(UserFact).order_by(
                UserFact.importance.desc(),
                UserFact.updated_at.desc(),
            )
        )
    ).scalars().all()
    return [_to_response(r) for r in rows]


@router.post("/facts", response_model=FactResponse, status_code=201)
async def create_fact(
    body: FactCreate,
    db: AsyncSession = Depends(get_db),
):
    """Manually add a user fact."""
    fact = UserFact(
        fact=body.fact,
        category=body.category,
        importance=body.importance,
        topics=body.topics,
        expires_at=body.expires_at,
    )
    db.add(fact)
    await db.flush()
    await db.refresh(fact)
    return _to_response(fact)


@router.put("/facts/{fact_id}", response_model=FactResponse)
async def update_fact(
    fact_id: uuid.UUID,
    body: FactUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a user fact in-place (preserves access stats and history)."""
    result = await db.execute(select(UserFact).where(UserFact.id == fact_id))
    fact = result.scalar_one_or_none()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    fact.fact = body.fact
    fact.category = body.category
    fact.importance = body.importance
    fact.topics = body.topics
    fact.expires_at = body.expires_at
    if body.verified_by_user is not None:
        fact.verified_by_user = body.verified_by_user
    await db.flush()
    await db.refresh(fact)
    return _to_response(fact)


@router.delete("/facts/{fact_id}")
async def delete_fact(
    fact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a user fact."""
    result = await db.execute(select(UserFact).where(UserFact.id == fact_id))
    fact = result.scalar_one_or_none()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    await db.delete(fact)
    return {"ok": True}
