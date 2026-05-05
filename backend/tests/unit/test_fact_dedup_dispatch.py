"""Unit tests for the dialect dispatch in save_user_fact's dedup query."""

from sqlalchemy.dialects import postgresql, sqlite

from app.ai.memory.facts import _dedup_candidate_stmt


def _compile(stmt, dialect_module) -> str:
    """Render the SQL the dispatcher emits, with literal binds, for assertions.

    We don't care about exact whitespace — just whether the right operators
    show up — so the comparison below is always lowercase + substring.
    """
    return str(stmt.compile(
        dialect=dialect_module.dialect(),
        compile_kwargs={"literal_binds": True},
    )).lower()


def test_postgres_dispatch_uses_trigram_similarity():
    sql = _compile(
        _dedup_candidate_stmt("save 50M for car", "postgresql", 0.85),
        postgresql,
    )
    assert "similarity(" in sql
    assert "0.85" in sql
    assert "order by" in sql  # ranked by score desc so the closest hit wins


def test_sqlite_dispatch_falls_back_to_exact_equality():
    sql = _compile(
        _dedup_candidate_stmt("save 50M for car", "sqlite", 0.85),
        sqlite,
    )
    assert "similarity(" not in sql  # no pg_trgm on SQLite
    assert "user_facts.fact = 'save 50m for car'" in sql


def test_threshold_is_passed_through():
    """Threshold change must reach the SQL — guards against accidental hard-coding."""
    sql = _compile(
        _dedup_candidate_stmt("x", "postgresql", 0.42),
        postgresql,
    )
    assert "0.42" in sql


# ── _strip_code_fence ────────────────────────────────────────────────────────


def test_strip_code_fence_plain_json():
    from app.ai.memory.facts import _strip_code_fence

    assert _strip_code_fence('[{"action": "add"}]') == '[{"action": "add"}]'


def test_strip_code_fence_code_fence():
    from app.ai.memory.facts import _strip_code_fence

    raw = '```json\n[{"action": "add"}]\n```'
    assert _strip_code_fence(raw) == '[{"action": "add"}]'


def test_strip_code_fence_deepseek_think_tags():
    """DeepSeek reasoning models prepend <think>...</think> before the JSON array."""
    from app.ai.memory.facts import _strip_code_fence

    raw = (
        "<think>\nAnalyzing the conversation carefully...\n</think>\n"
        '[{"action": "add", "fact": "User saves 5M/month"}]'
    )
    result = _strip_code_fence(raw)
    assert result == '[{"action": "add", "fact": "User saves 5M/month"}]'


def test_strip_code_fence_preamble_text():
    """Handles 'Here is the JSON:' style preamble before the array."""
    from app.ai.memory.facts import _strip_code_fence

    raw = 'Here are the extracted facts:\n[{"action": "add", "fact": "test"}]'
    result = _strip_code_fence(raw)
    assert result == '[{"action": "add", "fact": "test"}]'


def test_strip_code_fence_empty_array():
    from app.ai.memory.facts import _strip_code_fence

    assert _strip_code_fence("[]") == "[]"
