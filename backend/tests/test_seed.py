"""Tests for seed data logic."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.setting import Setting
from app.services.seed import seed


async def test_seed_creates_defaults(db: AsyncSession):
    await seed(db)
    await db.flush()

    cats = (await db.execute(select(Category))).scalars().all()
    assert len(cats) == 18  # 5 income + 12 expense + 1 both

    settings = (await db.execute(select(Setting))).scalars().all()
    assert len(settings) == 4


async def test_seed_is_idempotent(db: AsyncSession):
    await seed(db)
    await db.flush()
    await seed(db)  # second run should be no-op
    await db.flush()

    cats = (await db.execute(select(Category))).scalars().all()
    assert len(cats) == 18  # no duplicates
