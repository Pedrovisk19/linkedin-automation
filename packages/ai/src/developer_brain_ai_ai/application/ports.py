"""Application ports: AIProvider (chat/embed/stream), MemoryService (anti-repetition)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ChatResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str


@dataclass(frozen=True)
class EmbedResponse:
    embedding: list[float]
    model: str


@dataclass(frozen=True)
class ChatRequest:
    messages: list[ChatMessage]
    temperature: float = 0.4
    max_tokens: int | None = None
    response_format: type[BaseModel] | None = None


class AIProvider(Protocol):
    """Abstracao unica p/ todos os provedores (OpenAI, Claude, Gemini, ...)."""

    name: str

    async def chat(self, request: ChatRequest) -> ChatResponse: ...

    def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]: ...

    async def embed(self, text: str) -> EmbedResponse: ...


class MemoryService(Protocol):
    """Memoria persistente: grava fragmentos + busca por similaridade anti-repeticao."""

    async def remember(self, fragment) -> None: ...

    async def recall_similar(
        self, tenant_id, embedding: list[float], top_k: int = 6, source_module: str | None = None
    ) -> list: ...

    async def already_seen(self, tenant_id, key: str) -> bool: ...


__all__ = [
    "AIProvider",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "EmbedResponse",
    "MemoryService",
]
