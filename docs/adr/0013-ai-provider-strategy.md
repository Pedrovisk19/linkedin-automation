# ADR-0013 — AIProvider: 1 Protocol, M Strategy implementations

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
Múltiplos provedores de IA (OpenAI, Claude, Gemini, DeepSeek, OpenRouter) precisam ser
trocáveis por config sem tocar use cases dos agentes. Cada SDK tem sua API própria.

## Decision
Definir **um Protocol único** (`AIProvider`) com 3 contratos estáveis:
- `chat(ChatRequest) -> ChatResponse` (wrapper async)
- `chat_stream(ChatRequest) -> AsyncIterator[str]` (streaming de tokens)
- `embed(text) -> EmbedResponse`

`ChatRequest` / `ChatResponse` são dataclasses neutras (`messages: list[ChatMessage]`,
`prompt_tokens`, etc.) — nenhuma key OpenAI vaza. Cada provedor concreto (Strategy)
implementa este Protocol via ducktyping (sem herança explícita).

Troca de provedor: substituir uma instância no composition root; use cases continuam
funcionando pois dependem do Protocol, não de classes concretas.

Para structured outputs: `ChatRequest.response_format: type[BaseModel] | None` —
provedores que suportam (OpenAI, Gemini) usam; os que não suportam fazem fallback para
prompting com instruções de JSON e parsing posterior (`SummaryAgent._parse_output`
tolera JSON inválido).

## Consequences
- ✅ Adicionar provedor novo = nova classe em `infrastructure/`, zero mudança em use cases.
- ✅ Testes dos agentes usam `FakeAIProvider` determinístico (sem chave real).
- ✅ Troca de provedor é uma mudança de config/runtime, não de código.
- ⚠️ Streaming de OpenAI é assíncrono; `chat_stream` retorna AsyncIterator (consumidores
  precisam consumir async).
- ⚠️ Structured output sem suporte do modelo deixa de ser checagem de schema em runtime;
  mitigado por fallback com parsing defensivo.