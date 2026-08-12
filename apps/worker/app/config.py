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
    openai_base_url: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-large"
    ai_temperature: float = 0.4
    ai_max_tokens: int = 4096
    ai_language: str = "pt-BR"
    ai_writing_tone: str = "desenvolvedor-compartilhando-evolucao"

    #: hora do cron diario (UTC)
    pipeline_hour: int = 7
    pipeline_minute: int = 0

    #: news fetch cron — a cada 4 horas (0,4,8,12,16,20 UTC)
    news_fetch_hour: str = "0,4,8,12,16,20"
    news_fetch_minute: int = 0
    #: news digest cron — diario 08:00 UTC
    news_digest_hour: int = 8
    news_digest_minute: int = 0
    #: tenant alvo do digest de news (single-tenant por enquanto)
    news_tenant_id: str = ""

    #: Discord (aprovacao do digest via REST; o gateway roda na API)
    discord_bot_token: str = ""
    discord_allowed_channel_id: str = ""
    discord_tenant_id: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
