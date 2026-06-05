"""Scoring, topic normalization, and expiry helpers for user facts."""

from datetime import UTC, datetime, timedelta

from app.ai.memory.prompts import CANONICAL_TOPICS, CATEGORY_DEFAULT_TOPICS
from app.config import settings

_DEFAULT_SCORE = 5


def _clamp_score(raw: object) -> int:
    """Coerce a reviewer-emitted 1-10 score into the valid band.

    Shared by the importance and confidence pipelines: both fields have the
    same shape and same failure mode (Haiku occasionally emits floats, strings,
    or None), and one bad value shouldn't poison ordering for the rest.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return _DEFAULT_SCORE
    value = int(raw)
    if value < 1:
        return 1
    if value > 10:
        return 10
    return value


# Importance and confidence are semantically distinct (priority vs certainty)
# but share the same 1-10 shape and the same Haiku failure modes — bind both
# names to the one validator so they can never drift apart.
_clamp_importance = _clamp_score
_clamp_confidence = _clamp_score

# Maps common free-form tags Haiku might emit (despite instructions) to canonical.
_TOPIC_ALIASES: dict[str, str] = {
    "lương": "thu nhập", "salary": "thu nhập", "income": "thu nhập", "bonus": "thu nhập",
    "expenses": "chi tiêu", "spending": "chi tiêu", "expense": "chi tiêu", "tiêu": "chi tiêu",
    "budget": "ngân sách",
    "savings": "tiết kiệm", "save": "tiết kiệm",
    "goal": "mục tiêu", "target": "mục tiêu",
    "investment": "đầu tư", "invest": "đầu tư", "stock": "đầu tư", "crypto": "đầu tư",
    "debt": "nợ", "loan": "nợ", "credit": "nợ",
    "account": "tài khoản",
    "plan": "kế hoạch", "planning": "kế hoạch", "strategy": "kế hoạch",
    "subscription": "định kỳ", "recurring": "định kỳ",
    "food": "ăn uống", "dining": "ăn uống",
    "transport": "di chuyển", "vehicle": "di chuyển", "fuel": "di chuyển", "xe": "di chuyển",
    "housing": "nhà ở", "rent": "nhà ở", "nhà": "nhà ở",
    "shopping": "mua sắm", "clothes": "mua sắm",
    "health": "sức khỏe", "insurance": "sức khỏe", "medical": "sức khỏe",
    "entertainment": "giải trí", "leisure": "giải trí", "hobby": "giải trí",
    "education": "giáo dục", "course": "giáo dục", "books": "giáo dục",
    "family": "gia đình", "spouse": "gia đình", "children": "gia đình",
    "work": "công việc", "career": "công việc", "business": "công việc",
    "travel": "du lịch", "vacation": "du lịch",
    "habit": "thói quen", "routine": "thói quen", "pattern": "thói quen",
    "emotion": "cảm xúc", "feeling": "cảm xúc", "avoidance": "cảm xúc",
}

_CANONICAL_SET: frozenset[str] = frozenset(CANONICAL_TOPICS)


def _normalize_topics(raw: object, category: str) -> list[str]:
    """Map raw Haiku-emitted tags to canonical vocabulary.

    1. Accept tags already in the canonical set.
    2. Map known aliases (e.g. 'lương' → 'thu nhập').
    3. Drop anything unrecognized.
    4. Fall back to category default when nothing survives.
    """
    items = raw if isinstance(raw, list) else []
    result: list[str] = []
    seen: set[str] = set()
    for t in items:
        if not isinstance(t, str):
            continue
        normalized = t.lower().strip()
        canonical = normalized if normalized in _CANONICAL_SET else _TOPIC_ALIASES.get(normalized)
        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    if not result:
        result = list(CATEGORY_DEFAULT_TOPICS.get(category, []))
    return result[:3]


def _compute_expiry(
    item: dict,
    category: str,
    context_ttl_days: int | None = None,
) -> datetime | None:
    """Translate the reviewer's 'expires_in_days' hint into an absolute datetime.

    Defaults to the configured fallback TTL only for 'context' facts — the
    most common source of time-bound info (roles, life stages). Other
    categories stay evergreen unless the reviewer says otherwise.
    """
    raw = item.get("expires_in_days")
    days: float | None = None
    if isinstance(raw, (int, float)) and raw > 0:
        days = float(raw)
    elif raw is None and category == "context":
        days = float(context_ttl_days or settings.user_fact_default_context_ttl_days)
    if days is None:
        return None
    return datetime.now(UTC) + timedelta(days=days)
