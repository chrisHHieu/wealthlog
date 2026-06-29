"""Unit tests for the Tavily web tools (search + extract).

No network: httpx is replaced with a fake client. Covers registration gating
(no key → no tools), result formatting with the external-content note, and the
extract self-cap that keeps a long page under the history-compaction budget.
"""

from mcp.server.fastmcp import FastMCP

from app.ai.mcp.tools import web

# ── Fake httpx ──────────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, json_data: dict):
        self._json = json_data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._json


class _FakeClient:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.last_body: dict | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def post(self, _url, json=None, headers=None):
        self.last_body = json
        return self._response


def _patch_httpx(monkeypatch, response: _FakeResponse) -> _FakeClient:
    client = _FakeClient(response)
    monkeypatch.setattr(web.httpx, "AsyncClient", lambda *a, **k: client)
    return client


class _QueueClient:
    """Returns queued responses in order; records every request body."""

    def __init__(self, responses: list[_FakeResponse]):
        self._responses = list(responses)
        self.bodies: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def post(self, _url, json=None, headers=None):
        self.bodies.append(json)
        return self._responses.pop(0)


def _patch_httpx_queue(monkeypatch, responses: list[_FakeResponse]) -> _QueueClient:
    # A fresh client per AsyncClient() call, but all share one body log + queue.
    state = _QueueClient(responses)

    class _Proxy:
        async def __aenter__(self):
            return state

        async def __aexit__(self, *_):
            return False

    monkeypatch.setattr(web.httpx, "AsyncClient", lambda *a, **k: _Proxy())
    return state


async def _call(mcp: FastMCP, name: str, args: dict) -> str:
    result = await mcp.call_tool(name, args)
    contents = result[0] if isinstance(result, tuple) else result
    return "\n".join(c.text for c in contents if hasattr(c, "text"))


# ── _format_search (pure) ────────────────────────────────────────────────────


def test_format_search_includes_note_answer_and_citations():
    payload = {
        "answer": "Gold is up today.",
        "results": [
            {"title": "Gold price", "url": "https://x.com/gold",
             "content": "SJC at 78M", "published_date": "2026-06-24"},
        ],
    }
    out = web._format_search("giá vàng", "finance", payload)
    assert "EXTERNAL WEB CONTENT" in out
    assert "Gold is up today." in out
    assert "https://x.com/gold" in out
    assert "[2026-06-24]" in out
    assert "topic=finance" in out


def test_format_search_handles_no_results():
    out = web._format_search("nothing", "general", {"results": []})
    assert "No results found." in out


# ── registration gating ──────────────────────────────────────────────────────


async def test_register_is_noop_without_key(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "")
    mcp = FastMCP("test")
    web.register(mcp)
    names = {t.name for t in await mcp.list_tools()}
    assert "web_search" not in names
    assert "web_extract" not in names


async def test_register_adds_tools_with_key(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    mcp = FastMCP("test")
    web.register(mcp)
    names = {t.name for t in await mcp.list_tools()}
    assert {"web_search", "web_extract"} <= names


# ── global renumbering (citation alignment) ──────────────────────────────────


def test_renumber_search_text_offsets_markers():
    text = "Web results\n\n1. A\n   https://a.com\n   snip\n2. B\n   https://b.com\n   snip"
    new, count = web.renumber_search_text(text, 5)
    assert count == 2
    assert "6. A" in new and "7. B" in new
    assert "1. A" not in new


def test_renumber_search_text_no_markers_is_noop():
    text = "Extracted from https://x.com:\n\nbody text with 1. not a header"
    new, count = web.renumber_search_text(text, 3)
    assert count == 0
    assert new == text


# ── web_search behavior ──────────────────────────────────────────────────────


async def test_web_search_sends_lean_body_and_formats(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    client = _patch_httpx(monkeypatch, _FakeResponse({
        "answer": "ans", "results": [{"title": "T", "url": "u", "content": "c"}],
    }))
    mcp = FastMCP("test")
    web.register(mcp)

    out = await _call(mcp, "web_search", {"query": "q", "topic": "finance",
                                          "time_range": "day"})

    assert client.last_body["include_raw_content"] is False
    assert client.last_body["include_answer"] is True
    assert client.last_body["topic"] == "finance"
    assert client.last_body["time_range"] == "day"
    assert "ans" in out


async def test_web_search_retries_without_time_range_when_empty(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    state = _patch_httpx_queue(monkeypatch, [
        _FakeResponse({"results": []}),  # first call with time_range → empty
        _FakeResponse({"results": [{"title": "T", "url": "u", "content": "c"}]}),
    ])
    mcp = FastMCP("test")
    web.register(mcp)

    out = await _call(mcp, "web_search", {"query": "q", "time_range": "day"})

    assert len(state.bodies) == 2
    assert "time_range" in state.bodies[0]
    assert "time_range" not in state.bodies[1]  # retry dropped the filter
    assert "1. T" in out


async def test_web_search_does_not_retry_when_first_call_has_results(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    state = _patch_httpx_queue(monkeypatch, [
        _FakeResponse({"results": [{"title": "T", "url": "u", "content": "c"}]}),
    ])
    mcp = FastMCP("test")
    web.register(mcp)

    await _call(mcp, "web_search", {"query": "q", "time_range": "day"})
    assert len(state.bodies) == 1  # no retry needed


async def test_web_search_normalizes_bad_topic_and_drops_bad_time_range(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    client = _patch_httpx(monkeypatch, _FakeResponse({"results": []}))
    mcp = FastMCP("test")
    web.register(mcp)

    await _call(mcp, "web_search", {"query": "q", "topic": "weird",
                                    "time_range": "decade"})

    assert client.last_body["topic"] == "general"
    assert "time_range" not in client.last_body


async def test_web_search_passes_valid_dates_and_rejects_bad_format(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    client = _patch_httpx(monkeypatch, _FakeResponse({
        "results": [{"title": "T", "url": "u", "content": "c"}],
    }))
    mcp = FastMCP("test")
    web.register(mcp)

    await _call(mcp, "web_search", {"query": "q", "topic": "news",
                                    "start_date": "2026-03-01", "end_date": "March"})

    assert client.last_body["start_date"] == "2026-03-01"
    assert "end_date" not in client.last_body  # bad format dropped


async def test_web_search_retry_drops_all_date_filters_when_empty(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    state = _patch_httpx_queue(monkeypatch, [
        _FakeResponse({"results": []}),  # empty with date filters
        _FakeResponse({"results": [{"title": "T", "url": "u", "content": "c"}]}),
    ])
    mcp = FastMCP("test")
    web.register(mcp)

    await _call(mcp, "web_search", {"query": "q", "topic": "news",
                                    "time_range": "week", "start_date": "2026-03-01"})

    assert len(state.bodies) == 2
    assert {"time_range", "start_date"} <= state.bodies[0].keys()
    assert not ({"time_range", "start_date", "end_date"} & state.bodies[1].keys())


# ── web_extract behavior ─────────────────────────────────────────────────────


async def test_web_search_advanced_depth_passes_through(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    client = _patch_httpx(monkeypatch, _FakeResponse({
        "results": [{"title": "T", "url": "u", "content": "c"}],
    }))
    mcp = FastMCP("test")
    web.register(mcp)

    await _call(mcp, "web_search", {"query": "q", "search_depth": "advanced"})
    assert client.last_body["search_depth"] == "advanced"


async def test_web_search_bad_depth_falls_back_to_basic(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    client = _patch_httpx(monkeypatch, _FakeResponse({"results": []}))
    mcp = FastMCP("test")
    web.register(mcp)

    await _call(mcp, "web_search", {"query": "q", "search_depth": "turbo"})
    assert client.last_body["search_depth"] == "basic"


async def test_web_search_country_validated_and_general_only(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    client = _patch_httpx(monkeypatch, _FakeResponse({
        "results": [{"title": "T", "url": "u", "content": "c"}],
    }))
    mcp = FastMCP("test")
    web.register(mcp)

    # Valid country on general → normalized and sent.
    await _call(mcp, "web_search", {"query": "q", "topic": "general", "country": "Vietnam"})
    assert client.last_body["country"] == "vietnam"

    # Invalid country → dropped up front (no 400 round-trip).
    await _call(mcp, "web_search", {"query": "q", "topic": "general", "country": "atlantis"})
    assert "country" not in client.last_body

    # Valid country off the general topic → ignored.
    await _call(mcp, "web_search", {"query": "q", "topic": "finance", "country": "vietnam"})
    assert "country" not in client.last_body


async def test_search_fallback_retries_without_country_on_400(monkeypatch):
    """Safety net: if Tavily 400s on a country (e.g. enum drift), drop it and retry."""
    class _Resp400:
        status_code = 400

    def _raise():
        raise web.httpx.HTTPStatusError("bad", request=None, response=_Resp400())

    bad = _FakeResponse({})
    bad.raise_for_status = _raise
    state = _patch_httpx_queue(monkeypatch, [
        bad,
        _FakeResponse({"results": [{"title": "T", "url": "u", "content": "c"}]}),
    ])

    payload = await web._search_with_fallback({"query": "q", "country": "vietnam"})

    assert len(state.bodies) == 2
    assert "country" in state.bodies[0]
    assert "country" not in state.bodies[1]
    assert payload["results"]


async def test_web_extract_sends_markdown_and_query(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    client = _patch_httpx(monkeypatch, _FakeResponse({
        "results": [{"raw_content": "# Page"}],
    }))
    mcp = FastMCP("test")
    web.register(mcp)

    await _call(mcp, "web_extract", {"url": "https://x.com", "query": "gold price"})
    assert client.last_body["format"] == "markdown"
    assert client.last_body["query"] == "gold price"


async def test_web_extract_omits_query_when_absent(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    client = _patch_httpx(monkeypatch, _FakeResponse({"results": [{"raw_content": "x"}]}))
    mcp = FastMCP("test")
    web.register(mcp)

    await _call(mcp, "web_extract", {"url": "https://x.com"})
    assert "query" not in client.last_body


async def test_web_extract_trims_long_page(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    long_text = "A" * (web._EXTRACT_MAX_CHARS + 5000)
    _patch_httpx(monkeypatch, _FakeResponse({"results": [{"raw_content": long_text}]}))
    mcp = FastMCP("test")
    web.register(mcp)

    out = await _call(mcp, "web_extract", {"url": "https://x.com"})

    assert "chars trimmed]" in out
    assert len(out) < len(long_text)
    assert "EXTERNAL WEB CONTENT" in out


async def test_web_extract_reports_empty_page(monkeypatch):
    monkeypatch.setattr(web.settings, "tavily_api_key", "tvly-test")
    _patch_httpx(monkeypatch, _FakeResponse({"results": []}))
    mcp = FastMCP("test")
    web.register(mcp)

    out = await _call(mcp, "web_extract", {"url": "https://x.com"})
    assert "Could not extract content" in out
