"""Testes do OpenAIProvider: usa FakeOpenAIClient deterministico, valida chamadas."""

from __future__ import annotations

import asyncio
import json

from ai_fakes import FakeOpenAIClient
from developer_brain_ai_ai.application.ports import ChatMessage, ChatRequest
from developer_brain_ai_ai.infrastructure.openai_provider import OpenAIProvider
from pydantic import BaseModel


class MyModel(BaseModel):
    title: str


def test_chat_returns_content_and_usage() -> None:
    client = FakeOpenAIClient(chat_content="hello world")
    provider = OpenAIProvider(client=client, chat_model="gpt-4o-mini")

    req = ChatRequest(messages=[ChatMessage(role="user", content="hi")], temperature=0.2)
    out = asyncio.run(provider.chat(req))

    assert out.content == "hello world"
    assert out.model == "gpt-4o-mini"
    assert out.prompt_tokens == 10
    assert out.completion_tokens == 20


def test_chat_passes_temperature_and_max_tokens() -> None:
    client = FakeOpenAIClient(chat_content="x")
    provider = OpenAIProvider(client=client)
    req = ChatRequest(
        messages=[ChatMessage(role="user", content="hi")], temperature=0.7, max_tokens=42
    )
    asyncio.run(provider.chat(req))
    kw = client.chat.last_kwargs
    assert kw["temperature"] == 0.7
    assert kw["max_tokens"] == 42


def test_chat_includes_response_format_schema_when_set() -> None:
    client = FakeOpenAIClient(chat_content=json.dumps({"title": "ok"}))
    provider = OpenAIProvider(client=client)
    req = ChatRequest(
        messages=[ChatMessage(role="user", content="hi")],
        response_format=MyModel,
    )
    asyncio.run(provider.chat(req))
    kw = client.chat.last_kwargs
    assert "response_format" in kw
    assert kw["response_format"]["type"] == "json_schema"
    assert "title" in kw["response_format"]["json_schema"]["schema"]["properties"]


def test_chat_without_response_format_skips_key() -> None:
    client = FakeOpenAIClient(chat_content="plain")
    provider = OpenAIProvider(client=client)
    asyncio.run(provider.chat(ChatRequest(messages=[ChatMessage(role="user", content="hi")])))
    assert "response_format" not in client.chat.last_kwargs


def test_chat_stream_yields_chunks_one_per_line() -> None:
    client = FakeOpenAIClient(chat_content="line1\nline2\nline3")
    provider = OpenAIProvider(client=client)

    async def collect() -> list[str]:
        chunks: list[str] = []
        async for tok in provider.chat_stream(
            ChatRequest(messages=[ChatMessage(role="user", content="hi")])
        ):
            chunks.append(tok)
        return chunks

    out = asyncio.run(collect())
    assert out == ["line1", "line2", "line3"]


def test_embed_returns_vector() -> None:
    client = FakeOpenAIClient(embedding=[0.4, 0.5, 0.6])
    provider = OpenAIProvider(client=client)
    out = asyncio.run(provider.embed("hello"))
    assert out.embedding == [0.4, 0.5, 0.6]
    assert client.embeddings.calls == 1


def test_provider_name_is_openai() -> None:
    assert OpenAIProvider(client=FakeOpenAIClient()).name == "openai"
