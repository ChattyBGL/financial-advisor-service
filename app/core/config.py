from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "financial-advisor-service"
    app_version: str = "0.1.0"
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    debug: bool = False
    log_level: str = "INFO"

    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Postgres connection parameters (driver is psycopg 3)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("")
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout_seconds: float = 30.0
    db_pool_recycle_seconds: int = 1800
    db_echo: bool = False

    # Groq LLM (read from env, never hard-code the key)
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_timeout_seconds: float = 30.0
    groq_max_retries: int = 2

    @property
    def database_url(self) -> URL:
        """SQLAlchemy URL assembled from the individual DB settings.
        `URL.create` escapes special characters in the password for you."""
        return URL.create(
            drivername="postgresql+psycopg",
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            username=self.db_user,
            password=self.db_password.get_secret_value(),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
