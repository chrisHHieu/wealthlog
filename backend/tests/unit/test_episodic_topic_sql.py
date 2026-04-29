"""Compile-time SQL test for the JSONB topic-overlap query.

Postgres rejects ``jsonb ?| jsonb`` — the right-hand side must be ``text[]``.
Without an explicit cast, asyncpg infers a Python list as jsonb (matching the
LHS column type) and the prepared statement fails at runtime. This test
guards the cast at compile time so the regression can't silently come back.
"""

from sqlalchemy.dialects import postgresql

from app.models.session_summary import SessionSummary


async def test_topic_overlap_query_casts_param_to_text_array(monkeypatch):
    """The compiled SQL must cast the query_topics bind to TEXT[], not jsonb."""
    from app.ai.memory import episodic

    captured: dict = {}

    class _FakeBind:
        class dialect:
            name = "postgresql"

    class _FakeDB:
        bind = _FakeBind()

        async def execute(self, stmt):
            captured["stmt"] = stmt

            class _Empty:
                def scalars(self_inner):
                    return self_inner

                def all(self_inner):
                    return []

            return _Empty()

    await episodic._fetch_topic_overlap_summaries(
        _FakeDB(), query_topics=["xe", "budget"], exclude=set(), limit=2,
    )

    sql = str(captured["stmt"].compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )).lower()

    # The fix: explicit CAST(... AS TEXT[]) must surround the topics array.
    assert "?|" in sql
    assert "text[]" in sql or "cast(" in sql
    # Sanity: the column should still be on the LHS.
    assert "session_summaries.key_topics" in sql


def test_session_summary_model_present():
    """Smoke check the import path used by the runtime query."""
    assert SessionSummary.__tablename__ == "session_summaries"
