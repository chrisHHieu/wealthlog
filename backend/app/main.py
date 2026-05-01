import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.memory.decay import decay_old_facts, purge_expired_facts
from app.config import settings
from app.database import async_session
from app.logging_config import get_logger, setup_logging
from app.services.seed import seed
from app.routers import (
    accounts,
    budgets,
    categories,
    chat,
    dashboard,
    digest,
    goals,
    investments,
    memory,
    onboard,
    recurring,
    reports,
    settings as settings_router,
    transactions,
)

logger = get_logger(__name__)


def _run_migrations() -> None:
    """Run Alembic migrations to head via subprocess."""
    import subprocess
    import sys
    from pathlib import Path

    cwd = str(Path(__file__).resolve().parent.parent)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=cwd, capture_output=True, text=True,
    )
    if result.returncode != 0:
        logger.error("Alembic migration failed: %s", result.stderr)
        raise RuntimeError(f"Alembic migration failed: {result.stderr}")
    for line in result.stderr.strip().splitlines():
        logger.info("Alembic: %s", line)


async def _fact_decay_loop() -> None:
    """Run importance decay and expired-fact purge once per day."""
    while True:
        await asyncio.sleep(24 * 60 * 60)
        try:
            await decay_old_facts()
        except Exception:
            logger.exception("Scheduled fact decay failed")
        try:
            await purge_expired_facts()
        except Exception:
            logger.exception("Scheduled fact purge failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Startup and shutdown events."""
    setup_logging()
    logger.info("Starting %s", settings.app_name)
    logger.info("Debug mode: %s", settings.debug)
    logger.info("Database: %s", _mask_db_url(settings.database_url))

    _run_migrations()
    logger.info("Database migrations applied")

    async with async_session() as session:
        await seed(session)
        await session.commit()

    asyncio.create_task(_fact_decay_loop())

    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(chat.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(recurring.router)
app.include_router(budgets.router)
app.include_router(goals.router)
app.include_router(investments.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(settings_router.router)
app.include_router(memory.router)
app.include_router(onboard.router)
app.include_router(digest.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": settings.app_name}


def _mask_db_url(url: str) -> str:
    """Mask password in database URL for safe logging."""
    if "@" not in url:
        return url
    prefix, suffix = url.split("@", 1)
    if ":" in prefix:
        parts = prefix.rsplit(":", 1)
        return f"{parts[0]}:****@{suffix}"
    return url
