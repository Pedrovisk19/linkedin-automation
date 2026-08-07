# ADR-0004 — pgvector como vector store

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
RAG exige vector store. Opções: pgvector (Postgres), Qdrant dedicado, Pinecone cloud.

## Decision
Adotar **pgvector** já que o PostgreSQL está na stack. Extensão `vector` com índices
`HNSW`. Tabelas `documents`, `chunks`, `embeddings` vivem no mesmo banco.

## Consequences
- ✅ Zero infra nova; transações ACID cruzam domínio + embeddings.
- ✅ Migração via Alembic; backups unificados.
- ⚠️ Em escala (>10M vetores) pode-se trocar por Qdrant — interface `VectorStorePort`
  isola a troca (ISP).
- ⚠️ Recurso de memória do Postgres compartilhado entre OLTP e ANN — monitorar.