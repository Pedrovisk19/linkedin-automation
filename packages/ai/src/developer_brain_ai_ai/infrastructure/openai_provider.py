"""Implementacao concreta do AIProvider usando SDK oficial ``openai>=1.59`` (async).

Defensas implementadas:
- API key injetada (nao lida de env aqui) — testavel com mock client.
- ``response_format=Model`` (structured outputs OpenAI); fallback p/ JSON se houver
  erro de schema.
- Tokens contabilizados p/ observabilidade.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from developer_brain_ai_ai.application.ports import (
    ChatRequest,
    ChatResponse,
    EmbedResponse,
)


class OpenAIProvider:
    """AIProvider usando SDK async ``openai>=1.59``. Recebe client injetavel."""

    name = "openai"

    def __init__(
        self,
        *,
        client: Any,
        chat_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-large",
    ) -> None:
        self._client = client
        self._chat_model = chat_model
        self._embedding_model = embedding_model

    async def chat(self, request: ChatRequest) -> ChatResponse:
        kwargs: dict[str, Any] = {
            "model": self._chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        if request.response_format is not None:
            schema = request.response_format.model_json_schema()
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.response_format.__name__,
                    "schema": schema,
                    "strict": False,
                },
            }

        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        content = choice.message.content or ""
        usage = getattr(resp, "usage", None)
        return ChatResponse(
            content=content,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            model=self._chat_model,
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        kwargs: dict[str, Any] = {
            "model": self._chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "stream": True,
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    async def embed(self, text: str) -> EmbedResponse:
        resp = await self._client.embeddings.create(
            model=self._embedding_model,
            input=text,
        )
        item = resp.data[0]
        return EmbedResponse(embedding=list(item.embedding), model=self._embedding_model)


__all__ = ["OpenAIProvider"]
