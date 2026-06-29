"""OpenTelemetry tracing for the agent loop.

Tracing is opt-in (``settings.otel_enabled``): when off, the OTel API hands back
a no-op tracer and spans cost nothing. When on, ``setup_tracing`` installs an SDK
provider — OTLP if ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, else the console
exporter. The runner wraps each LLM call and each tool execution in a span via
:func:`trace_span`, so a slow turn can be decomposed into model-vs-tool time.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

_TRACER_NAME = "wealthlog.agent"


def setup_tracing() -> None:
    """Install an SDK tracer provider if tracing is enabled. Idempotent."""
    if not settings.otel_enabled:
        return
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return  # already installed

    provider = TracerProvider(resource=Resource.create({"service.name": settings.app_name}))
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        except Exception:
            logger.warning("OTLP exporter unavailable — using console exporter")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    logger.info("OpenTelemetry tracing enabled")


def get_tracer() -> trace.Tracer:
    """Return the agent tracer (a no-op proxy until setup_tracing runs)."""
    return trace.get_tracer(_TRACER_NAME)


@asynccontextmanager
async def trace_span(
    name: str, attributes: dict | None = None,
) -> AsyncIterator[trace.Span]:
    """Start a current span with the given attributes (dotted OTel keys ok)."""
    with get_tracer().start_as_current_span(name) as span:
        for key, value in (attributes or {}).items():
            if value is not None:
                span.set_attribute(key, value)
        yield span
