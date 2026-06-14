"""Unit tests for read-time staleness decay (lazy decay)."""

from datetime import UTC, datetime, timedelta

from app.ai.memory.fact_scoring import (
    EFFECTIVE_IMPORTANCE_FLOOR,
    STALENESS_STEP_DAYS,
    effective_importance,
)

_NOW = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)


def _aged(days: int) -> datetime:
    return _NOW - timedelta(days=days)


def test_fresh_fact_keeps_full_importance():
    assert effective_importance(8, False, _aged(0), _NOW) == 8
    assert effective_importance(8, False, _aged(STALENESS_STEP_DAYS - 1), _NOW) == 8


def test_one_point_lost_per_step():
    assert effective_importance(8, False, _aged(STALENESS_STEP_DAYS), _NOW) == 7
    assert effective_importance(8, False, _aged(STALENESS_STEP_DAYS * 3), _NOW) == 5


def test_floor_is_never_crossed():
    assert effective_importance(5, False, _aged(3650), _NOW) == EFFECTIVE_IMPORTANCE_FLOOR
    assert effective_importance(1, False, _aged(3650), _NOW) == EFFECTIVE_IMPORTANCE_FLOOR


def test_verified_facts_are_exempt():
    """User vouched for it — time alone must not erode trust."""
    assert effective_importance(7, True, _aged(3650), _NOW) == 7


def test_missing_updated_at_means_no_penalty():
    assert effective_importance(6, False, None, _NOW) == 6


def test_naive_datetime_is_treated_as_utc():
    """SQLite returns naive datetimes; they must not crash or skew the math."""
    naive = (_NOW - timedelta(days=STALENESS_STEP_DAYS * 2)).replace(tzinfo=None)
    assert effective_importance(8, False, naive, _NOW) == 6


def test_future_updated_at_keeps_full_importance():
    """Clock skew must never inflate the penalty."""
    assert effective_importance(8, False, _NOW + timedelta(days=2), _NOW) == 8
