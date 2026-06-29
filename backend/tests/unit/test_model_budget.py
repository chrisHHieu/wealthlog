"""Per-model context window + input budget derivation."""

from app.ai.model_registry import (
    _DEFAULT_CONTEXT_WINDOW,
    _OUTPUT_RESERVE_MARGIN,
    context_window,
    effective_input_budget,
)
from app.config import settings


def test_context_window_matched_by_prefix():
    # Opus/Sonnet 4.x are 1M; Haiku stays 200K; specific families beat the
    # generic "claude" fallback.
    assert context_window("claude-sonnet-4-6") == 1_000_000
    assert context_window("claude-opus-4-8") == 1_000_000
    assert context_window("claude-haiku-4-5") == 200_000
    assert context_window("deepseek-v4-pro") == 1_000_000


def test_context_window_unknown_falls_back_to_safe_default():
    assert context_window("some-future-model") == _DEFAULT_CONTEXT_WINDOW


def test_large_window_model_is_bounded_by_the_cost_cap():
    # 1M window → the per-turn cost cap is the binding limit, not the window.
    assert effective_input_budget("deepseek-v4-pro") == settings.agent_max_input_tokens


def test_small_window_model_is_bounded_by_the_window():
    # An unknown (small-default) model must be capped UNDER its window so the
    # request leaves room for output — never overflow into a 400.
    expected = _DEFAULT_CONTEXT_WINDOW - (settings.agent_max_tokens + _OUTPUT_RESERVE_MARGIN)
    assert effective_input_budget("tiny-context-model") == expected
    assert expected < settings.agent_max_input_tokens  # window, not cost, binds here


def test_budget_always_leaves_room_for_output():
    # input + output must fit inside the window for every known model.
    for model in ("claude-sonnet-4-6", "deepseek-v4-pro", "unknown-x"):
        budget = effective_input_budget(model)
        assert budget + settings.agent_max_tokens < context_window(model)
