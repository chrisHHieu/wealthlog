"""Goals CRUD + contributions router."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.logging_config import get_logger
from app.models.goal import Goal, GoalContribution
from app.schemas.finance.goal import GoalAddAmount, GoalCreate, GoalResponse, GoalUpdate

logger = get_logger(__name__)
router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("", response_model=list[GoalResponse])
async def list_goals(db: AsyncSession = Depends(get_db)) -> list[Goal]:
    result = await db.execute(
        select(Goal).options(selectinload(Goal.contributions)).order_by(Goal.created_at)
    )
    return list(result.scalars().all())


@router.post("", response_model=GoalResponse, status_code=201)
async def create_goal(
    body: GoalCreate,
    db: AsyncSession = Depends(get_db),
) -> Goal:
    goal = Goal(**body.model_dump())
    db.add(goal)
    await db.flush()
    await db.refresh(goal)
    await db.refresh(goal, attribute_names=["contributions"])
    logger.info("Created goal '%s'", goal.name)
    return goal


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Goal:
    result = await db.execute(
        select(Goal).options(selectinload(Goal.contributions)).where(Goal.id == goal_id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: uuid.UUID,
    body: GoalUpdate,
    db: AsyncSession = Depends(get_db),
) -> Goal:
    goal = await db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    await db.flush()
    await db.refresh(goal)
    await db.refresh(goal, attribute_names=["contributions"])
    logger.info("Updated goal %s", goal_id)
    return goal


@router.post("/{goal_id}/contribute", response_model=GoalResponse)
async def add_contribution(
    goal_id: uuid.UUID,
    body: GoalAddAmount,
    db: AsyncSession = Depends(get_db),
) -> Goal:
    result = await db.execute(
        select(Goal).options(selectinload(Goal.contributions)).where(Goal.id == goal_id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    contribution = GoalContribution(
        goal_id=goal_id,
        amount=body.amount,
        note=body.note,
        date=body.date,
    )
    db.add(contribution)

    goal.current_amount += body.amount
    if goal.current_amount >= goal.target_amount:
        goal.is_completed = True

    await db.flush()
    await db.refresh(goal)
    await db.refresh(goal, attribute_names=["contributions"])
    logger.info("Added %.2f contribution to goal %s", body.amount, goal_id)
    return goal


@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    goal = await db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    await db.delete(goal)
    await db.flush()
    logger.info("Deleted goal %s", goal_id)
    return {"success": True}
