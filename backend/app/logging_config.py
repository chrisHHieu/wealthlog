import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from logging import LogRecord
from typing import Any

from app.config import settings

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

_STANDARD_RECORD_KEYS = frozenset(vars(LogRecord("", 0, "", 0, "", (), None)).keys())


def get_request_id() -> str | None:
    """Return the request ID bound to the current context, if any."""
    return _request_id.get()


def set_request_id(request_id: str):
    """Bind a request ID to the current context and return the reset token."""
    return _request_id.set(request_id)


def reset_request_id(token) -> None:
    """Reset request ID context after a request finishes."""
    _request_id.reset(token)


class JsonLogFormatter(logging.Formatter):
    """JSON log formatter with request context and safe exception rendering."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if request_id := get_request_id():
            payload["request_id"] = request_id

        extras = {
            key: value
            for key, value in vars(record).items()
            if key not in _STANDARD_RECORD_KEYS and not key.startswith("_")
        }
        payload.update(extras)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging() -> None:
    """Configure structured logging for the application."""
    log_level = logging.DEBUG if settings.debug else logging.INFO

    formatter = JsonLogFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Root logger
    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance."""
    return logging.getLogger(name)
