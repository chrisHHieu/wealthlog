from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://wealthlog:wealthlog2026@localhost:5433/wealthlog"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # CORS
    cors_origins: list[str] = ["http://localhost:3001"]

    # AI Agent
    anthropic_api_key: str = ""
    agent_model: str = "claude-haiku-4-5-20251001"
    agent_max_tokens: int = 4096
    agent_tool_result_max_chars: int = 3000
    agent_max_history_tokens: int = 16000
    agent_review_model: str = "claude-haiku-4-5-20251001"
    agent_review_cadence: int = 6  # review every N turns
    mcp_server_url: str = "http://localhost:8002/sse"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8002

    # App
    debug: bool = False
    app_name: str = "WealthLog API"
    api_prefix: str = "/api"


settings = Settings()
