from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session, get_db
from app.logging_config import get_logger, reset_request_id, set_request_id, setup_logging
from app.routers import (
    accounts,
    budgets,
    categories,
    dashboard,
    goals,
    investments,
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Startup and shutdown events."""
    setup_logging()
    from app.ai.tracing import setup_tracing

    setup_tracing()
    logger.info("Starting %s", settings.app_name)
    logger.info("Debug mode: %s", settings.debug)
    logger.info("Database: %s", _mask_db_url(settings.database_url))

    _run_migrations()
    logger.info("Database migrations applied")

    async with async_session() as session:
        await seed(session)
        await session.commit()

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


# Register routers (finance only — chat/memory/AI moved to the Chip project)
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


@app.get("/health")
@app.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness: is the process responsive? No dependencies — checking the DB
    here would turn a transient DB blip into a mass pod-restart cascade.
    """
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/ready")
async def health_ready(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness: should this pod receive traffic? Checks the critical
    dependency (the database). The LLM is a hosted API with no in-process model
    to warm, so DB connectivity is the only gate. Returns 503 on failure so the
    load balancer drains this pod without restarting it.
    """
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("Readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready", "service": settings.app_name}


def _mask_db_url(url: str) -> str:
    """Mask password in database URL for safe logging."""
    if "@" not in url:
        return url
    prefix, suffix = url.split("@", 1)
    if ":" in prefix:
        parts = prefix.rsplit(":", 1)
        return f"{parts[0]}:****@{suffix}"
    return url
