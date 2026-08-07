# ADR-0001 — Multi-tenant desde o dia 1

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
O produto nasce como "segundo cérebro pessoal" mas o roadmap prevê SaaS. Adicionar
multi-tenancy depois custa refactor de schema, queries, auth e auditoria — experiência
clássica de "fazer seguro agora custa caro depois".

## Decision
Modelar **multi-tenant desde o dia 1** via:
- `tenant_id UUID NOT NULL` em toda tabela de domínio.
- **Row-Level Security (RLS)** no Postgres: policy por `app.tenant_id` (SET var de sessão
  no início de cada transação, via SQLAlchemy `before_connect`/UoW).
- `User` pertence a um `Tenant`; auth JWT carrega `tenant_id`.
- Migrações Alembic reaplicam policies.

## Consequences
- ✅ Isolamento forte no banco (defesa em profundidade, não só app-layer).
- ✅ Caminho para SaaS sem refactor de domínio.
- ✅ Performance: RLS usa índice em `(tenant_id)` — partial/BTREE.
- ⚠️ setups de testes precisam rodar com role não-superuser para que RLS atue.
- ⚠️ Migrations e seeds precisam setar `BYRLS` com cuidado (role `monton` para DDL).
- ⚠️ Curva inicial: ~1 sprint para fundação de tenancy.