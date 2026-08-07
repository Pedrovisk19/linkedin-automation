# ADR-0005 — Arq como background worker / scheduler

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
Pipeline diário (diário → resumo → LinkedIn → README → newsletter → cards → dashboard
→ histórico) exige um scheduler. Opções: APScheduler (in-processo), Celery+Beat
(maduro/síncrono), Arq (async/Redis).

## Decision
Adotar **Arq**: async nativo, leve, usa Redis (já na stack) e combina com FastAPI
(asyncio). Jobs declarados como funções async com `async with` no `PoolSettings`.

## Consequences
- ✅ Sem scheduler in-process acoplado à API (escala isolada via apps/worker).
- ✅ Idempotência por chave de job (dedupe no Redis).
- ✅ Reusar `asyncpg`/`httpx` do mesmo eco-async.
- ⚠️ Ecossistema menor que Celery — mitigado pela simplicidade.
- ⚠️ Sem UI admin — previsto dashboard próprio para runs.