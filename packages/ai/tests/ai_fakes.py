"""Fakes p/ tests do modulo ai (sem OpenAI real, sem DB)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, UTC

from developer_brain_ai_ai.application.dto import SummaryAgentInput, SummaryAgentOutput
from developer_brain_ai_ai.application.ports import (
    AIProvider,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    EmbedResponse,
)


class FakeAIProvider:
    """AIProvider deterministico p/ testes. ``chat`` retorna um JSON configuravel."""

    name = "fake"

    def __init__(self, *, chat_response: str = '{"title":"ok","markdown":"# R","top_learnings":[],"metrics":{}}') -> None:
        self._chat_response = chat_response
        self.last_request: ChatRequest | None = None
        self.calls = 0

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.calls += 1
        self.last_request = request
        return ChatResponse(content=self._chat_response, prompt_tokens=10, completion_tokens=20, model="fake-1")

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        for chunk in self._chat_response.split("\n"):
            yield chunk

    async def embed(self, text: str) -> EmbedResponse:
        return EmbedResponse(embedding=[0.1, 0.2, 0.3], model="fake-embed")


class FakeOpenAIClient:
    """Mock minimal do AsyncOpenAI. Suporta chat.completions.create + embeddings.create."""

    def __init__(self, *, chat_content: str = "", embedding: list[float] | None = None) -> None:
        self.chat = _ChatNamespace(chat_content)
        self.embeddings = _EmbeddingsNamespace(embedding or [0.1])


@dataclass
class _FakeUsage:
    prompt_tokens: int = 10
    completion_tokens: int = 20


@dataclass
class _FakeMessage:
    content: str


@dataclass
class _FakeChoice:
    message: _FakeMessage


@dataclass
class _FakeChatResp:
    choices: list
    usage: _FakeUsage = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.usage is None:
            self.usage = _FakeUsage()


class _ChatNamespace:
    def __init__(self, content: str) -> None:
        self._content = content
        self.completions = self
        self.last_kwargs: dict = {}

    async def create(self, **kwargs):  # noqa: ANN201
        self.last_kwargs = kwargs
        if kwargs.get("stream"):
            return _FakeChatStream(self._content)
        return _FakeChatResp(choices=[_FakeChoice(message=_FakeMessage(self._content))])


@dataclass
class _FakeDelta:
    content: str | None


@dataclass
class _FakeStreamChoice:
    delta: _FakeDelta


@dataclass
class _FakeStreamChunk:
    choices: list


class _FakeChatStream:
    def __init__(self, content: str) -> None:
        self._lines = content.split("\n")

    def __aiter__(self):  # noqa: ANN204
        return self

    async def __anext__(self):  # noqa: ANN204
        if not self._lines:
            raise StopAsyncIteration
        line = self._lines.pop(0)
        return _FakeStreamChunk(choices=[_FakeStreamChoice(delta=_FakeDelta(line))])


@dataclass
class _FakeEmbeddingItem:
    embedding: list[float]


@dataclass
class _FakeEmbeddingResp:
    data: list


class _EmbeddingsNamespace:
    def __init__(self, embedding: list[float]) -> None:
        self._emb = embedding
        self.calls = 0

    async def create(self, *, model, input):  # noqa: ANN201
        self.calls += 1
        return _FakeEmbeddingResp(data=[_FakeEmbeddingItem(self._emb)])


class FakeAgentRunRepository:
    def __init__(self) -> None:
        self.saved: list = []

    async def save(self, run) -> None:
        self.saved.append(run)

    async def list_recent(self, tenant_id, agent, limit: int = 50) -> list:
        return list(self.saved)


__all__ = ["FakeAIProvider", "FakeOpenAIClient", "FakeAgentRunRepository"]