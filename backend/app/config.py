from __future__ import annotations
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "TradePath AI"
    DEBUG: bool = False
    SQL_ECHO: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tradepath"
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    ELASTICSEARCH_URL: str = "http://localhost:9200"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1-mini-2025-04-14"

    # DeepInfra Whisper Large v3 — matches portfolio PDF spec
    DEEPINFRA_API_KEY: str = ""
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1/openai"
    WHISPER_MODEL: str = "openai/whisper-large-v3"
    MOCK_WHISPER: bool = False

    AZURE_DI_ENDPOINT: str = ""
    AZURE_DI_KEY: str = ""
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "trade-docs"

    # SDN / sanctions list update interval (hours)
    SDN_REFRESH_HOURS: int = 4

    # CORS / Rate limiting
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    RATE_LIMIT_PER_MINUTE: int = 60

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        weak = {"change-me-in-production", "change-me-before-production", "secret", ""}
        if v.lower() in weak or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 chars and not a known weak default")
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
