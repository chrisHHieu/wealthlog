"""Unit tests for the tracing helpers using an in-memory span exporter."""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.ai.tracing import trace_span


@pytest.fixture
def span_exporter():
    """Install an isolated in-memory provider for the duration of one test.

    OTel forbids replacing a real provider, so we set one only if the global is
    still the default no-op proxy; otherwise we reuse it and just swap exporters
    by adding our own processor.
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    current = trace.get_tracer_provider()
    if not isinstance(current, TracerProvider):
        trace.set_tracer_provider(provider)
        tracer_provider = provider
    else:
        current.add_span_processor(SimpleSpanProcessor(exporter))
        tracer_provider = current
    yield exporter
    tracer_provider.force_flush()


async def test_trace_span_records_span_with_attributes(span_exporter):
    async with trace_span("agent.tool", {"tool.name": "create_transaction"}) as span:
        span.set_attribute("tool.is_error", False)

    spans = span_exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert "agent.tool" in names
    tool_span = next(s for s in spans if s.name == "agent.tool")
    assert tool_span.attributes["tool.name"] == "create_transaction"
    assert tool_span.attributes["tool.is_error"] is False


async def test_trace_span_skips_none_attributes(span_exporter):
    async with trace_span("agent.llm_call", {"agent.model": None, "agent.iteration": 1}):
        pass

    span = next(s for s in span_exporter.get_finished_spans() if s.name == "agent.llm_call")
    assert "agent.model" not in span.attributes
    assert span.attributes["agent.iteration"] == 1
