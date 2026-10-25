"""Application settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for CivicLens.

    All values are read from environment variables or a .env file.
    No secrets or defaults with real values live in source code.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://civiclens:changeme@localhost:5432/civiclens",
        description="Async PostgreSQL connection string",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and rate-limiting",
    )

    # Anthropic / LLM
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key for RAG narrator and governance tasks",
    )

    # Application behaviour
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG | INFO | WARNING | ERROR",
    )
    environment: str = Field(
        default="development",
        description="Runtime environment: development | staging | production",
    )

    # Scraper settings
    scraper_rate_limit_rps: float = Field(
        default=1.0,
        description="Max requests per second for all scrapers",
    )
    scraper_max_retries: int = Field(
        default=3,
        description="Tenacity retry attempts per request",
    )
    scraper_respect_robots: bool = Field(
        default=True,
        description=(
            "Honour robots.txt. Set False for public government portals that "
            "disallow bots globally but publish data for public consumption."
        ),
    )
    data_raw_dir: str = Field(
        default="data/raw",
        description="Root directory for raw ingested files",
    )

    @property
    def is_production(self) -> bool:
        """Return True when running in production."""
        return self.environment == "production"


settings = Settings()
