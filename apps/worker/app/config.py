"""Worker settings via pydantic-settings (espelha o config da API)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    app_log_level: str = "INFO"
    app_log_json: bool = False

    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10

    arq_redis_url: str = "redis://redis:6379/0"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-large"
    ai_language: str = "pt-BR"
    ai_writing_tone: str = "desenvolvedor-compartilhando-evolucao"

    #: hora do cron diario (UTC)
    pipeline_hour: int = 7
    pipeline_minute: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
