from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://wealthlog:wealthlog2026@localhost:5433/wealthlog"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3001"]

    # ── Anthropic / AI agent ─────────────────────────────────────────────────
    anthropic_api_key: str = ""
    agent_model: str = "claude-haiku-4-5-20251001"
    agent_max_tokens: int = 4096
    agent_thinking_enabled: bool = True
    agent_thinking_budget: int = 2000

    # ── Short-term memory (in-session compaction) ────────────────────────────
    # 3-tier strategy: turns older than `max_turns_in_context` are dropped,
    # the middle window has tool_result payloads truncated, and the recent
    # window passes through — unless a single recent turn itself exceeds
    # `recent_turn_max_chars`, in which case its earlier tool_results fall back
    # to the middle-tier limit (keeping the last result intact for final-answer
    # grounding). `max_input_tokens` is a soft pre-send budget used only for
    # warning logs so we can spot runaway sessions before Anthropic does.
    agent_max_turns_in_context: int = 20
    agent_keep_recent_turns: int = 3
    agent_tool_result_max_chars: int = 3000
    agent_old_turn_tool_result_chars: int = 300
    agent_recent_turn_max_chars: int = 20_000
    agent_max_input_tokens: int = 150_000

    # ── Long-term memory (facts extraction) ──────────────────────────────────
    agent_review_model: str = "claude-haiku-4-5-20251001"
    agent_review_cadence: int = 6
    user_fact_default_context_ttl_days: int = 90

    # ── Long-term memory (episodic session summaries) ────────────────────────
    session_summary_model: str = "claude-haiku-4-5-20251001"
    session_summary_idle_minutes: int = 30
    session_summary_max_recent: int = 5

    # ── MCP server (stdio/SSE entry point for external clients) ──────────────
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8002

    # ── App ──────────────────────────────────────────────────────────────────
    debug: bool = False
    app_name: str = "WealthLog API"


settings = Settings()
