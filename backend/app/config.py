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
    # DeepSeek API key — nếu set, DeepSeek models sẽ xuất hiện trong UI model picker.
    deepseek_api_key: str = ""
    # Sonnet for the main agent — it reasons across user model, facts, and tool
    # results in a single turn, so model quality directly affects advice depth.
    agent_model: str = "claude-sonnet-4-6"
    agent_max_tokens: int = 8000
    agent_thinking_enabled: bool = True
    # Sonnet's extended thinking window is much larger; 8k lets it properly
    # reason through multi-step financial questions.
    agent_thinking_budget: int = 8000

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
    agent_old_turn_tool_result_chars: int = 600
    agent_recent_turn_max_chars: int = 20_000
    agent_max_input_tokens: int = 150_000

    # ── Long-term memory (facts extraction) ──────────────────────────────────
    agent_review_cadence: int = 6
    user_fact_default_context_ttl_days: int = 90
    # Trigram similarity threshold for save_user_fact() dedup. 0.85 is high
    # enough to avoid collapsing genuinely distinct facts, low enough to catch
    # paraphrases the reviewer emits across sessions. Postgres-only; SQLite
    # falls back to exact-match equality.
    user_fact_dedup_similarity_threshold: float = 0.85
    # When the non-expired fact count crosses this, the post-review pipeline
    # asks Haiku to merge overlapping rows via 'replace' actions. Capped to
    # bound prompt size: more facts = more tokens to inject every turn.
    user_fact_consolidation_threshold: int = 100

    session_summary_idle_minutes: int = 30
    session_summary_max_recent: int = 5
    # Within `max_recent`, reserve up to N slots for older sessions whose
    # key_topics overlap the current user message — recovers "remember when
    # we discussed X" without needing embeddings. Set to 0 to disable.
    session_summary_topic_hits: int = 2

    # ── Long-term memory (UserModel synthesis) ───────────────────────────────
    user_model_synthesis_cadence: int = 5   # synthesize after every N new sessions
    user_model_fact_delta_threshold: int = 5  # also synthesize when N new facts added since last run
    user_model_max_versions: int = 3        # keep last N versions, prune older ones

    # ── MCP server (stdio/SSE entry point for external clients) ──────────────
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8002

    # ── App ──────────────────────────────────────────────────────────────────
    debug: bool = False
    app_name: str = "WealthLog API"


settings = Settings()
