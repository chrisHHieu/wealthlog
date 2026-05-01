"""Centralized model resolution — reads the user's preferred model from DB.

All AI subsystems (chat agent, fact review, session summary, synthesis,
digest) call ``get_preferred_model()`` so a single UI toggle propagates
everywhere.  Falls back to the ``.env`` default when no preference is stored.
"""

from app.config import settings
from app.database import get_session
from app.logging_config import get_logger
from app.models.setting import Setting

logger = get_logger(__name__)

# DB key used in the settings key-value table.
_PREFERRED_MODEL_KEY = "preferredModel"


async def get_preferred_model() -> str:
    """Return the user-chosen model, falling back to ``settings.agent_model``."""
    try:
        async with get_session() as db:
            row = await db.get(Setting, _PREFERRED_MODEL_KEY)
            if row and row.value:
                return row.value
    except Exception:
        logger.debug("Could not read preferred model from DB — using env default")
    return settings.agent_model


async def set_preferred_model(model_id: str) -> None:
    """Persist the user's model choice to the settings table."""
    async with get_session() as db:
        existing = await db.get(Setting, _PREFERRED_MODEL_KEY)
        if existing:
            existing.value = model_id
        else:
            db.add(Setting(key=_PREFERRED_MODEL_KEY, value=model_id))


def resolve_client_kwargs(model: str) -> dict:
    """Return the Anthropic client constructor kwargs for the given model.

    Handles DeepSeek models transparently — callers don't need to know
    which provider backs the model string.
    """
    is_deepseek = model.startswith("deepseek-")
    kwargs: dict = {
        "api_key": settings.deepseek_api_key if is_deepseek else settings.anthropic_api_key,
    }
    if is_deepseek:
        kwargs["base_url"] = "https://api.deepseek.com/anthropic"
    return kwargs
