"""Settings request/response schemas."""

from app.schemas.base import CamelModel


class SettingsUpdate(CamelModel):
    """Bulk update settings as key-value pairs."""

    data: dict[str, str]


class SettingsResponse(CamelModel):
    """All settings as a flat key-value map."""

    data: dict[str, str]
