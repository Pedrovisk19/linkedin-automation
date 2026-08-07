# Developer Brain AI

Segundo cérebro para desenvolvedores: diário técnico, roadmap, projetos, estudos,
biblioteca, agentes de IA (LinkedIn, GitHub, Planner, Summary, Career, Prompt Engineer),
memória persistente, RAG sobre a própria base, automações diárias e dashboard.

> Arquitetura Clean Architecture + DDD, multi-tenant desde o dia 1, monorepo UV workspace.
> Ver `docs/architecture.md` e `docs/adr/`.

## Stack

Python 3.14 · FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · PostgreSQL + pgvector ·
Redis · Arq · UV · Ruff/Black · MyPy · Docker · Next.js (futuro) · Nginx · GitHub Actions.

## Início rápido

```bash
make dev            # sobe postgres+pgvector, redis, api, worker via docker compose
make migrate        # roda alembic upgrade head
make test           # pytest com cobertura
make lint           # ruff + mypy
make shell-db       # psql no banco
```

## Estrutura

```
apps/        api (FastAPI) + worker (Arq)
packages/    bounded contexts (Clean Architecture por módulo)
prompts/     prompts .md editáveis
docs/        ADRs, diagramas, arquitetura
infra/       Dockerfiles + docker-compose
web/         Next.js (futuro)
```

Veja `docs/architecture.md` para o modelo de domínio, camadas e fluxo do pipeline diário.