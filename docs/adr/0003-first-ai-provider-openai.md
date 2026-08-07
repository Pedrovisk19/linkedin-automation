# ADR-0003 — OpenAI como primeiro provedor de IA

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
A camada `AIProvider` abstrai todos os modelos, mas precisamos de UM concreto para
validar interfaces, agentes e RAG. Candidatos: OpenAI, Claude, DeepSeek, OpenRouter.

## Decision
Implementar **OpenAI** primeiro:
- Chat: `gpt-4o-mini` (default) configurável.
- Embeddings: `text-embedding-3-large` (3072 dims) — base para RAG.
- Structured outputs via Pydantic.

Outros provedores entram quando a interface já estiver validada (Strategy pattern).

## Consequences
- ✅ Embeddings + chat no mesmo provedor simplifica RAG da fase 8.
- ✅ SDK oficial Python estável.
- ⚠️ Custo recorrente — mitigado por `AI_TEMPERATURE`/`AI_MAX_TOKENS` e cache de prompts.
- ⚠️ Vendor lock-in parcial — mitigado pela abstração `AIProvider`.