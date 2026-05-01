"""Onboarding — collects initial user facts via a structured wizard.

Two endpoints:
  GET  /api/onboard/status  — whether the user has completed onboarding
  POST /api/onboard         — submit wizard data, saves verified facts + triggers synthesis
"""

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import Field
from sqlalchemy import func, select

from app.ai.memory.facts import save_user_fact
from app.ai.memory.synthesis import force_synthesize_user_model
from app.database import get_session
from app.logging_config import get_logger
from app.models.user_fact import UserFact
from app.schemas.base import CamelModel

logger = get_logger(__name__)
router = APIRouter(prefix="/api/onboard", tags=["onboard"])


# ── Request schemas ───────────────────────────────────────────────────────────

class OnboardGoal(CamelModel):
    name: str
    amount: int | None = None          # VND target
    deadline: str | None = None        # YYYY-MM-DD


class OnboardRequest(CamelModel):
    monthly_income: int | None = None
    income_source: str | None = None   # salary | freelance | business | other
    household: str | None = None       # single | couple | family
    dependents: int | None = None
    monthly_expenses_estimate: int | None = None
    current_savings: int | None = None
    has_debt: bool | None = None
    debt_amount: int | None = None
    goals: list[OnboardGoal] = Field(default_factory=list)
    main_concerns: list[str] = Field(default_factory=list)


# ── Response schemas ──────────────────────────────────────────────────────────

class OnboardStatus(CamelModel):
    is_onboarded: bool
    fact_count: int


class OnboardResult(CamelModel):
    facts_saved: int
    synthesis_scheduled: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(amount: int) -> str:
    return f"{amount:,} VND"


def _build_facts(req: OnboardRequest) -> list[tuple[str, str, int]]:
    """Convert onboarding request into (fact_text, category, importance) tuples."""
    facts: list[tuple[str, str, int]] = []

    # Income
    if req.monthly_income:
        source = f" ({req.income_source})" if req.income_source else ""
        facts.append((
            f"Monthly income: ~{_fmt(req.monthly_income)}{source}",
            "context", 10,
        ))

    # Household
    if req.household:
        dep_str = ""
        if req.dependents:
            dep_str = f" with {req.dependents} dependent(s)"
        facts.append((f"Household: {req.household}{dep_str}", "context", 8))

    # Monthly expenses estimate
    if req.monthly_expenses_estimate:
        facts.append((
            f"Estimated monthly expenses: ~{_fmt(req.monthly_expenses_estimate)}",
            "context", 8,
        ))

    # Current savings
    if req.current_savings is not None:
        facts.append((
            f"Current savings/cash: ~{_fmt(req.current_savings)}",
            "context", 9,
        ))

    # Debt
    if req.has_debt is True and req.debt_amount:
        facts.append((
            f"Has existing debt: ~{_fmt(req.debt_amount)} total",
            "context", 9,
        ))
    elif req.has_debt is False:
        facts.append(("No existing debt", "context", 7))

    # Goals
    for g in req.goals:
        parts = [f"Goal: {g.name}"]
        if g.amount:
            parts.append(f"target {_fmt(g.amount)}")
        if g.deadline:
            parts.append(f"by {g.deadline}")
        facts.append((" — ".join(parts), "goal", 9))

    # Main concerns → preferences
    if req.main_concerns:
        concerns_str = ", ".join(req.main_concerns)
        facts.append((
            f"Main financial concerns: {concerns_str}",
            "preference", 8,
        ))

    return facts


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=OnboardStatus)
async def onboard_status():
    """Check whether the user has completed onboarding.

    'Onboarded' means at least one verified fact exists. The frontend uses
    this to decide whether to show the onboarding wizard on first launch.
    """
    async with get_session() as db:
        count = (
            await db.execute(
                select(func.count(UserFact.id)).where(
                    UserFact.verified_by_user.is_(True)
                )
            )
        ).scalar_one()

    return OnboardStatus(is_onboarded=count > 0, fact_count=count)


@router.post("", response_model=OnboardResult, status_code=201)
async def submit_onboarding(body: OnboardRequest):
    """Submit onboarding wizard data.

    Converts structured inputs into UserFacts with verified_by_user=True and
    importance=9-10, then schedules an immediate UserModel synthesis so the
    agent has a coherent user profile from the very first conversation.
    """
    fact_tuples = _build_facts(body)
    if not fact_tuples:
        raise HTTPException(
            status_code=422,
            detail="No usable data provided. Fill in at least one field.",
        )

    saved = 0
    for text, category, importance in fact_tuples:
        result = await save_user_fact(
            fact=text,
            category=category,
            importance=importance,
            confidence=10,          # user-provided = maximum confidence
            verified_by_user=True,  # onboarding data is user-confirmed by definition
        )
        if result["status"] == "saved":
            saved += 1

    logger.info("Onboarding complete — %d facts saved", saved)

    # Trigger synthesis immediately so the agent has a UserModel from turn 1.
    asyncio.create_task(force_synthesize_user_model())

    return OnboardResult(facts_saved=saved, synthesis_scheduled=True)
