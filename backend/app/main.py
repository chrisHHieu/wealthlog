import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.ai.memory.decay import purge_expired_facts, sunset_stale_facts
from app.ai.memory.dreaming import run_dreaming_pass
from app.config import settings
from app.database import async_session
from app.logging_config import get_logger, reset_request_id, set_request_id, setup_logging
from app.routers import (
    accounts,
    budgets,
    categories,
    chat,
    chat_sessions,
    dashboard,
    digest,
    goals,
    investments,
    memory,
    onboard,
    recurring,
    reports,
    transactions,
)
from app.routers import (
    settings as settings_router,
)
from app.services.seed import seed

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


async def _memory_maintenance_loop() -> None:
    """Daily memory upkeep: sunset stale facts, dream over expired ones, purge.

    Staleness itself is priced into ranking at read time (lazy decay in
    fact_scoring.effective_importance) — this loop only runs the destructive
    tail. Order matters — the dreaming pass rewrites expired facts into
    past-tense outcome facts, so it must run before the purge deletes them.
    """
    while True:
        await asyncio.sleep(24 * 60 * 60)
        try:
            await sunset_stale_facts()
        except Exception:
            logger.exception("Scheduled fact sunset failed")
        try:
            await run_dreaming_pass()
        except Exception:
            logger.exception("Scheduled dreaming pass failed")
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

    asyncio.create_task(_memory_maintenance_loop())

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


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    token = set_request_id(request_id)
    started = perf_counter()
    try:
        response = await call_next(request)
        duration_ms = round((perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "HTTP request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    except Exception:
        duration_ms = round((perf_counter() - started) * 1000, 2)
        logger.exception(
            "HTTP request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise
    finally:
        reset_request_id(token)


# Register routers
app.include_router(chat.router)
app.include_router(chat_sessions.router)
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
