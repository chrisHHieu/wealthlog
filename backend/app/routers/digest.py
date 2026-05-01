"""Weekly digest endpoints.

  GET  /api/digest/latest   — return the most recent saved digest
  POST /api/digest/generate — generate a new digest and save it
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.ai.digest import generate_digest, get_latest_digest, save_digest
from app.logging_config import get_logger
from app.schemas.base import CamelModel

logger = get_logger(__name__)
router = APIRouter(prefix="/api/digest", tags=["digest"])


class DigestResponse(CamelModel):
    id: uuid.UUID
    content: str
    generated_for_month: str
    created_at: datetime


def _to_response(row) -> DigestResponse:
    return DigestResponse(
        id=row.id,
        content=row.content,
        generated_for_month=row.generated_for_month,
        created_at=row.created_at,
    )


@router.get("/latest", response_model=DigestResponse | None)
async def latest_digest():
    """Return the most recently generated digest, or null if none exist yet."""
    row = await get_latest_digest()
    return _to_response(row) if row else None


@router.post("/generate", response_model=DigestResponse, status_code=201)
async def generate_new_digest():
    """Generate a fresh weekly financial digest and save it.

    Calls financial MCP tools to gather real data, then synthesizes a
    structured report with Sonnet. Takes 5-15 seconds depending on data volume.
    """
    try:
        content = await generate_digest()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Digest generation failed")
        raise HTTPException(
            status_code=500, detail="Digest generation failed"
        ) from exc

    row = await save_digest(content)
    logger.info("Digest saved for month %s", row.generated_for_month)
    return _to_response(row)
