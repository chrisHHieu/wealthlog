"""Dashboard router — thin wrapper around ``services.dashboard_aggregator``."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.dashboard_aggregator import build_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    period: str = Query("6months"),
    month: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return the FE-shaped dashboard payload for the given period/month."""
    return await build_dashboard(db, period=period, month=month)
