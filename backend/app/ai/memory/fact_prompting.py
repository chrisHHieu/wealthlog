"""Prompt formatting helpers for user facts."""

CATEGORY_LABELS = {
    "preference": "Preference",
    "habit": "Habit",
    "goal": "Goal",
    "context": "Context",
    "pattern": "Pattern",
    "commitment": "Commitment",
    "emotion": "Emotion",
    "general": "General",
}


def topic_overlap(fact_topics: list[str], query_topics: list[str]) -> int:
    """Count token-level overlap between stored fact topics and query tokens."""
    if not fact_topics or not query_topics:
        return 0
    fact_tokens: set[str] = set()
    for topic in fact_topics:
        fact_tokens.update(topic.lower().split())
    query_tokens = {topic.lower() for topic in query_topics}
    return len(fact_tokens & query_tokens)


def rerank_facts_for_prompt(facts: list[dict], query_topics: list[str]) -> list[dict]:
    """Rank facts by importance, verification, and query topic overlap."""
    if not facts:
        return facts

    def score(fact: dict) -> int:
        base = fact["importance"] * 10 + (
            5 if fact.get("verified_by_user") else 0
        )
        return base + topic_overlap(fact.get("topics", []), query_topics) * 20

    return sorted(facts, key=score, reverse=True)


def format_facts_prompt(facts: list[dict]) -> str:
    """Format fact dictionaries into the system-prompt fact block."""
    if not facts:
        return ""

    lines = ["[Known facts about the user]"]
    for fact in facts:
        label = CATEGORY_LABELS.get(fact["category"], fact["category"])
        marker = "[✓] " if fact.get("verified_by_user") else ""
        topics_str = (
            " " + " ".join(f"#{topic}" for topic in fact["topics"])
            if fact.get("topics")
            else ""
        )
        lines.append(f"- {marker}({label}) {fact['fact']}{topics_str}")
    lines.append("[End of user facts]")

    return "\n".join(lines)
