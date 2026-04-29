"""Reports router — thin wrapper around ``services.reports_builder``."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.reports_builder import build_reports

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
async def get_reports(
    mode: str = Query("month"),
    month: str | None = Query(None),
    year: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return the FE-shaped reports payload for the given mode/period."""
    return await build_reports(db, mode=mode, month=month, year=year)
