"""Shared Pydantic config and utilities."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CamelModel(BaseModel):
    """Base model that converts snake_case fields to camelCase in JSON output."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i else word
            for i, word in enumerate(field_name.split("_"))
        ),
    )


class UUIDResponse(CamelModel):
    """Mixin for responses that include a UUID id."""

    id: uuid.UUID


class TimestampResponse(UUIDResponse):
    """Mixin for responses with id + created_at + updated_at."""

    created_at: datetime
    updated_at: datetime


class CreatedAtResponse(UUIDResponse):
    """Mixin for responses with id + created_at only."""

    created_at: datetime


class PaginatedResponse[T](CamelModel):
    """Generic paginated list response."""

    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
