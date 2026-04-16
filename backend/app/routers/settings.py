"""Settings get/upsert router."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.setting import Setting
from app.schemas.setting import SettingsResponse, SettingsUpdate

logger = get_logger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsResponse:
    result = await db.execute(select(Setting))
    rows = result.scalars().all()
    data = {row.key: row.value for row in rows}
    return SettingsResponse(data=data)


@router.put("")
async def update_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    for key, value in body.data.items():
        existing = await db.get(Setting, key)
        if existing:
            existing.value = value
        else:
            db.add(Setting(key=key, value=value))
    await db.flush()
    logger.info("Updated %d settings", len(body.data))
    return {"success": True}
