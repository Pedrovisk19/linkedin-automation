"""Arq worker composition root (stub). Jobs registrados em Fase 7."""
from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings


async def startup(ctx: dict) -> None:
    ctx.setdefault("ok", True)


async def daily_pipeline(ctx: dict) -> None:
    # Implementado em Fase 7 (automation.use_cases.RunDailyPipeline).
    raise NotImplementedError("daily pipeline definido em Fase 7")


class WorkerSettings:
    functions: list = []
    cron_jobs = [cron(daily_pipeline, hour=7, minute=0)]
    on_startup = startup
    redis_settings = RedisSettings()