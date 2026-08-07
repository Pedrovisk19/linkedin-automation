# ADR-0007 — Monorepo UV workspace + Clean Architecture por bounded context

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
12+ bounded contexts (identity, journal, roadmap, projects, studies, library, ai,
content, integrations, rag, automation) + 2 apps (api, worker). Precisamos de isolamento
de regras de domínio, troca fácil de infra e testabilidade.

## Decision
- **Monorepo** único gerenciado por **UV workspace** (PEP 735).
- Cada bounded context = um pacote Python em `packages/<ctx>/` com 4 camadas:
  `domain` (puro, sem框架), `application` (use_cases + DTOs + ports),
  `infrastructure` (SMTP/SQLAlchemy/SDKs), `presentation` (FastAPI routers/esquemas).
- `apps/api` é **composition root**: monta DI, sobe FastAPI, registra routers dos contexts.
- `apps/worker` é composition root do Arq.
- `packages/shared` é o kernel (base entity, errors, UoW, tenant context, logging).

Regra de dependência: `domain ← application ← infrastructure ← presentation`.
Nenhuma referência de `domain` para SQLAlchemy/FastAPI/OpenAI.

## Consequences
- ✅ Refactors isolados por contexto; testes por pacote.
- ✅ Infra trocável sem tocar domínio (ISP — `Port` Protocol).
- ✅ Single venv, single lockfile — coerência de versões.
- ⚠️ boilerplate inicial maior — mitigado com templates por contexto.
- ⚠️ Cyclomatic imports supervisionados por tests de arquitetura (layering check).