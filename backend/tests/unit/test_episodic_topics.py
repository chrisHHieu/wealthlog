"""Unit tests for the query-topic extractor used by episodic retrieval."""

from app.ai.memory.episodic import _extract_query_topics


def test_empty_message_returns_empty():
    assert _extract_query_topics("") == []
    assert _extract_query_topics("   ") == []


def test_lowercases_and_dedupes_tokens():
    """Tokens normalize to lowercase; duplicates collapse, order preserved."""
    out = _extract_query_topics("Budget Budget BUDGET tracking")
    assert out == ["budget", "tracking"]


def test_drops_single_char_tokens():
    """Single-char tokens are noise; 2+ chars survive so Vietnamese words like 'xe' work."""
    out = _extract_query_topics("a I 1 xe đi của")
    assert "a" not in out
    assert "i" not in out
    assert "1" not in out
    assert "xe" in out
    assert "đi" in out
    assert "của" in out


def test_preserves_vietnamese_diacritics():
    """Haiku stores key_topics verbatim; tokenizer must keep diacritics for ?| match."""
    out = _extract_query_topics("Tôi muốn mua xe và tiết kiệm tiền")
    assert "muốn" in out
    assert "mua" in out
    assert "xe" in out
    assert "tiết" in out
    assert "kiệm" in out


def test_strips_punctuation():
    """Surrounding punctuation must not bleed into tokens."""
    out = _extract_query_topics("budget, ngân-sách! tiêu/dùng?")
    assert "budget" in out
    assert "ngân" in out
    assert "sách" in out
    assert "tiêu" in out
    assert "dùng" in out


def test_normalizes_unicode_form():
    """NFC normalization keeps composed/decomposed sequences comparable."""
    composed = _extract_query_topics("nợ")  # NFC
    decomposed = _extract_query_topics("nợ")  # NFD source — both should match
    assert composed == decomposed
