"""Model catalogue surfaced to the chat UI."""

from app.ai.model_registry import get_preferred_model, set_preferred_model
from app.config import settings

_ANTHROPIC_MODELS = [
    {
        "id": "claude-sonnet-4-6",
        "name": "Claude Sonnet 4.6",
        "description": "Cân bằng tốc độ và chất lượng",
    },
]

_DEEPSEEK_MODELS = [
    {
        "id": "deepseek-v4-pro",
        "name": "DeepSeek V4 Pro",
        "description": "Mạnh, chi phí thấp hơn Claude",
    },
]


async def list_available_models() -> dict:
    models = list(_ANTHROPIC_MODELS)
    if settings.deepseek_api_key:
        models += _DEEPSEEK_MODELS
    return {"models": models, "default": await get_preferred_model()}


async def save_preferred_model(model_id: str) -> str:
    await set_preferred_model(model_id)
    return model_id
