"""API settings via pydantic-settings. Single source of truth for runtime config."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    app_name: str = "developer-brain-ai"
    app_env: str = "local"
    app_log_level: str = "INFO"
    app_log_json: bool = False

    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    redis_host: str = "redis"
    redis_port: int = 6379
    arq_redis_url: str = "redis://redis:6379/0"

    jwt_secret: str
    jwt_alg: str = "HS256"
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 2_592_000

    ai_provider_default: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-large"
    ai_temperature: float = 0.4
    ai_max_tokens: int = 2000
    ai_language: str = "pt-BR"
    ai_writing_tone: str = "desenvolvedor-compartilhando-evolucao"

    storage_kind: str = "local"
    storage_local_root: str = "./data/uploads"

    rag_embedding_dim: int = 3072
    rag_top_k: int = 6

    obsidian_vault_path: str = "./data/obsidian-vault"
    tenant_default_id: str = "00000000-0000-0000-0000-000000000000"

    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = ""

    telegram_bot_token: str = ""
    telegram_allowed_chat_id: str = ""
    telegram_tenant_id: str = ""
    telegram_polling: bool = True

    discord_bot_token: str = ""
    discord_allowed_channel_id: str = ""
    discord_tenant_id: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
