# ADR-0009 — Estratégia de testes em camadas

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
Cobertura alvo ≥90% em 12+ contexts. Misturar testes de unidade e integração em uma
suite só sobe o feedback loop e dificulta isolar falhas.

## Decision
Três tiers de testes via markers do pytest:
- `unit` (default): dominio puro + use_cases com ports em fakes. Não toca IO.
- `integration` (marker): Postgres+pgvector + Redis reais (CI sobe via services GitHub Actions).
- `arch` (marker): testes de arquitetura (imports proibidos, dependências entre camadas).

Comando padrão `make test` roda todos. `make test-unit` filtra unidade. CI roda
`pytest -ra --cov=packages --cov=apps --cov-fail-under=90` (todos os tiers).

Fakes e fixtures vivem em `tests/` por pacote. DB de teste via `alembic upgrade head`
contra `DATABASE_URL` de CI.

## Consequences
- ✅ Testes de dominio sao rapidos (<100ms por suite).
- ✅ Camada application tem suas dependencias injetadas via Protocol — trivial mockar.
- ✅ Testes de arquitetura prevenvem vazamentos de verantwortlich (ex.: domain importando SQLAlchemy).
- ⚠️ Cada package tem seu proprio `tests/` junto — exige `coverage source = ["packages","apps"]` central.