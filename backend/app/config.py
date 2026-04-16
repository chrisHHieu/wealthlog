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

    # App
    debug: bool = True
    app_name: str = "WealthLog API"
    api_prefix: str = "/api"


settings = Settings()
