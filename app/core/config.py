from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Groq LLM (read from env, never hard-code the key)
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_timeout_seconds: float = 30.0
    groq_max_retries: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
