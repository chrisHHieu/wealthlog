"""Budgets CRUD + check router."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.finance.budget import BudgetCheckResponse, BudgetCreate, BudgetResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api/budgets", tags=["budgets"])


def _current_month() -> str:
    today = date.today()
    return f"{today.year}-{today.month:02d}"


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    month: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    month = month or _current_month()
    stmt = (
        select(
            Budget,
            Category.name.label("category_name"),
            Category.icon.label("category_icon"),
            Category.color.label("category_color"),
        )
        .outerjoin(Category, Budget.category_id == Category.id)
        .where(Budget.month == month)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            **{c.key: getattr(row[0], c.key) for c in row[0].__table__.columns},
            "category_name": row[1],
            "category_icon": row[2],
            "category_color": row[3],
        }
        for row in rows
    ]


@router.post("", response_model=BudgetResponse, status_code=201)
async def create_budget(
    body: BudgetCreate,
    db: AsyncSession = Depends(get_db),
):
    # Upsert: delete existing budget for same category+month
    await db.execute(
        delete(Budget).where(
            and_(Budget.category_id == body.category_id, Budget.month == body.month)
        )
    )
    budget = Budget(**body.model_dump())
    db.add(budget)
    await db.flush()
    logger.info("Upserted budget for category %s month %s", body.category_id, body.month)
    return budget


@router.delete("")
async def delete_budget(
    budget_id: uuid.UUID = Query(..., alias="id"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    budget = await db.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    await db.delete(budget)
    await db.flush()
    logger.info("Deleted budget %s", budget_id)
    return {"success": True}


@router.get("/check", response_model=BudgetCheckResponse | None)
async def check_budget(
    category_id: uuid.UUID = Query(..., alias="categoryId"),
    month: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    month = month or _current_month()

    # Find budget
    stmt = (
        select(Budget.amount)
        .where(and_(Budget.category_id == category_id, Budget.month == month))
    )
    row = (await db.execute(stmt)).first()
    if not row:
        return None

    budget_amount = row[0]

    # Calculate spending
    start_date = f"{month}-01"
    end_date = f"{month}-31"
    spent_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        and_(
            Transaction.category_id == category_id,
            Transaction.type == "expense",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
    )
    total_spent = (await db.execute(spent_q)).scalar() or 0
    percent = (total_spent / budget_amount * 100) if budget_amount > 0 else 0

    return BudgetCheckResponse(
        budget_amount=budget_amount,
        total_spent=total_spent,
        percent=round(percent),
        remaining=max(0, budget_amount - total_spent),
        is_exceeded=total_spent > budget_amount,
        is_warning=80 <= percent < 100,
    )
