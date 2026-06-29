from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://wealthlog:wealthlog2026@localhost:5433/wealthlog"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    # Proactively retire connections older than this (seconds). Cloud
    # infra (NAT gateways, managed-DB proxies, load balancers) silently drops
    # idle TCP connections; recycling below their idle timeout turns "server
    # closed the connection unexpectedly" into a non-event. pool_pre_ping is
    # the reactive complement. Default 1800s (30 min) sits under most defaults.
    db_pool_recycle: int = 1800

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3001"]

    # ── Anthropic / AI agent ─────────────────────────────────────────────────
    anthropic_api_key: str = ""
    # DeepSeek API key — nếu set, DeepSeek models sẽ xuất hiện trong UI model picker.
    deepseek_api_key: str = ""
    # Tavily web-search API key — nếu set, the agent gains web_search + web_extract
    # tools (live market prices, rates, news, reading a pasted URL). Cross-provider:
    # plain MCP tools, so every model (Claude, DeepSeek, …) can call them. When
    # empty the tools are simply not registered and the agent never sees them.
    tavily_api_key: str = ""
    # Sonnet for the main agent — it reasons across user model, facts, and tool
    # results in a single turn, so model quality directly affects advice depth.
    agent_model: str = "claude-sonnet-4-6"
    agent_max_tokens: int = 16000
    agent_thinking_enabled: bool = True
    # thinking_budget must be < max_tokens; 8k reasoning leaves ~8k for text output.
    agent_thinking_budget: int = 8000

    # ── Short-term memory (in-session compaction) ────────────────────────────
    # 3-tier strategy: turns older than `max_turns_in_context` are dropped,
    # the middle window has tool_result payloads truncated, and the recent
    # window passes through — unless a single recent turn itself exceeds
    # `recent_turn_max_chars`, in which case its earlier tool_results fall back
    # to the middle-tier limit (keeping the last result intact for final-answer
    # grounding). `max_input_tokens` is the pre-send budget: when the token
    # count exceeds it, the runner recompacts the raw history with a tighter
    # window (half the turns, recent window capped at 2) before sending.
    agent_max_turns_in_context: int = 40
    agent_keep_recent_turns: int = 6
    # Generous safety cap on a FRESH tool result (this turn). Tools already bound
    # their own output (LIMIT, top_n), so this rarely triggers — it only guards a
    # pathological dump. Kept high on purpose: the model needs the full result to
    # reason THIS turn ("fresh full"); shrinking happens later in history
    # compaction ("old compressed"), not on the live result. Set generously since
    # modern models have large context windows — web_extract/search benefit most.
    agent_tool_result_max_chars: int = 32_000
    agent_old_turn_tool_result_chars: int = 2_000
    # Per-turn ceiling for the recent window; sized above a couple of full-size
    # tool results so a multi-tool turn isn't squeezed before history compaction.
    agent_recent_turn_max_chars: int = 96_000
    # Pre-send INPUT cost cap (every input token is billed each turn). Our main
    # models hold ~1M tokens, so this is a deliberate cost/latency throttle, not a
    # technical limit — raise toward the window (≤~1M) to keep longer sessions
    # uncompacted; prompt caching makes the extra context mostly cheap cache reads.
    agent_max_input_tokens: int = 512_000

    # Financial write tools (create/update/delete transactions) are gated behind
    # explicit user confirmation: the agent's call is persisted as a pending
    # action and only executes when the user confirms it via the API. Set False
    # to let the agent write directly (not recommended for a money app).
    agent_require_write_confirmation: bool = True

    # ── Long-term memory (facts extraction) ──────────────────────────────────
    agent_review_cadence: int = 6
    # Output budget for ALL background memory LLM tasks (review, consolidation,
    # dreaming, synthesis, session summary). These run on the structured model,
    # which may be a REASONING model (e.g. DeepSeek) that spends part of the
    # budget on hidden thinking — set too low and the JSON output gets truncated
    # to empty and the task silently no-ops. They're background + infrequent, so a
    # generous ceiling costs little. (Foreground chat output uses agent_max_tokens.)
    memory_task_max_tokens: int = 16_000
    user_fact_default_context_ttl_days: int = 90
    # Transient categories (emotions, passing deliberations) default to a SHORT
    # TTL so a mood logged once doesn't persist as fact forever. The reviewer
    # can still override per-fact via 'expires_in_days'. Once expired, the daily
    # dreaming pass resolves the fact with its real outcome or drops it.
    user_fact_emotion_ttl_days: int = 30
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
    # Also synthesize when N new facts were added since last run.
    user_model_fact_delta_threshold: int = 5
    # Also synthesize if model is stale and any new data exists.
    user_model_max_age_days: int = 1
    user_model_max_versions: int = 3        # keep last N versions, prune older ones

    # ── MCP server (stdio/SSE entry point for external clients) ──────────────
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8002
    # Bearer token the SSE MCP server requires (and the agent sends). Empty =
    # no auth (dev/local only). Set in BOTH the mcp server and the agent.
    mcp_auth_token: str = ""

    # ── MCP client (the agent as an MCP Host) ────────────────────────────────
    # When set, the agent connects to this MCP server over SSE (the wire) instead
    # of the in-process server — the seam toward splitting Chip into its own
    # service. Empty = in-process (default). e.g. "http://mcp:8002/sse".
    mcp_server_url: str = ""

    # ── Observability ────────────────────────────────────────────────────────
    # Opt-in OpenTelemetry tracing of the agent loop (spans per LLM call + tool).
    # Off by default; when on, exports via OTLP if OTEL_EXPORTER_OTLP_ENDPOINT is
    # set, otherwise to the console.
    otel_enabled: bool = False

    # ── App ──────────────────────────────────────────────────────────────────
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("WEALTHLOG_DEBUG", "APP_DEBUG"),
    )
    app_name: str = "WealthLog API"


settings = Settings()
