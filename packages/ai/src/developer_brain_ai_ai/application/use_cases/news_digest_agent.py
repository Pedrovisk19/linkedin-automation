"""NewsDigestAgent: gera um NewsDigestDraft a partir de itens de fontes externas.

Nao persiste — apenas retorna output. Persistir em ContentDraft e
responsabilidade do composition root. Mantem o agente isolado e testavel
contra FakeAIProvider sem depender do modulo content/news.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow
from pydantic import BaseModel, Field

from developer_brain_ai_ai.application.ports import AIProvider, ChatMessage, ChatRequest
from developer_brain_ai_ai.application.prompt_engine import PromptEngine
from developer_brain_ai_ai.domain.aggregates import AgentRun
from developer_brain_ai_ai.domain.ids import AgentRunId
from developer_brain_ai_ai.domain.repositories import AgentRunRepository
from developer_brain_ai_ai.domain.value_objects import AgentName, PromptName

NEWS_DIGEST_AGENT = AgentName("news_digest")
NEWS_DIGEST_PROMPT = PromptName("news_digest")

_HASHTAG_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{1,49}$")


def _normalize_tag(raw: str) -> str:
    v = raw.strip()
    if v.startswith("#"):
        v = v[1:]
    return v.lower()


def _valid_tag(raw: str) -> bool:
    return bool(raw) and bool(_HASHTAG_RE.match(_normalize_tag(raw)))


class NewsDigestDraft(BaseModel):
    """Output bruto do digest. Hashtags normalizadas (sem # e lowercase)."""

    title: str = Field(default="")
    gancho: str = Field(default="")
    texto: str = Field(default="")
    conclusao: str = Field(default="")
    pergunta: str = Field(default="")
    cta: str = Field(default="")
    hashtags: list[str] = Field(default_factory=list)
    source_url_ids: list[str] = Field(default_factory=list)

    @classmethod
    def _normalize_tag(cls, raw: str) -> str:
        return raw.strip().lstrip("#").lower()

    @classmethod
    def _split_tags(cls, raw: Any) -> list[str]:
        chunks = raw if isinstance(raw, list) else [raw]
        tags: list[str] = []
        for chunk in chunks:
            if isinstance(chunk, str):
                tags.extend(re.split(r"[\s,;]+", chunk))
        return tags

    def __init__(self, **data: Any) -> None:
        tags: list[str] = []
        for t in self._split_tags(data.get("hashtags") or []):
            v = self._normalize_tag(t)
            if _HASHTAG_RE.match(v):
                tags.append(v)
        data["hashtags"] = tags
        super().__init__(**data)


@dataclass
class NewsDigestAgentConfig:
    temperature: float = 0.4
    max_tokens: int = 4096
    max_items: int = 6


class NewsDigestAgent:
    def __init__(
        self,
        *,
        provider: AIProvider,
        prompt_engine: PromptEngine,
        runs: AgentRunRepository,
        config: NewsDigestAgentConfig | None = None,
    ) -> None:
        self._provider = provider
        self._engine = prompt_engine
        self._runs = runs
        self._cfg = config or NewsDigestAgentConfig()

    async def execute(
        self,
        tenant_id: TenantId,
        *,
        items: list[dict[str, Any]],
        ai_writing_tone: str = "engenheiro-senior-confiante-dona-do-aprendizado",
        ai_language: str = "pt-BR",
    ) -> NewsDigestDraft:
        tpl = self._engine.load(NEWS_DIGEST_PROMPT)
        rendered_system = tpl.render(
            {
                "ai_writing_tone": ai_writing_tone,
                "ai_language": ai_language,
                "entries_blob": self._render_items(items),
            }
        )
        request = ChatRequest(
            messages=[
                ChatMessage(role="system", content=rendered_system),
                ChatMessage(
                    role="user",
                    content=(
                        "Gere o digest diário de Python em JSON (title, gancho, "
                        "texto, conclusao, pergunta, cta, hashtags). Baseie-se "
                        "SOMENTE nos itens fornecidos."
                    ),
                ),
            ],
            temperature=self._cfg.temperature,
            max_tokens=self._cfg.max_tokens,
            response_format=NewsDigestDraft,
        )
        started = datetime.now(UTC)
        response = await self._provider.chat(request)
        finished = datetime.now(UTC)

        source_ids = [str(i.get("id", "")) for i in items if i.get("id")]
        output = self._parse_output(response.content, source_ids)

        inputs_hash = hashlib.sha256(json.dumps({"items": items}, default=str).encode()).hexdigest()
        run = AgentRun(
            id=AgentRunId.new(),
            tenant_id=tenant_id,
            agent=NEWS_DIGEST_AGENT,
            prompt_name=NEWS_DIGEST_PROMPT,
            prompt_version=tpl.version,
            inputs_hash=inputs_hash,
            output_summary=output.title or "(no title)",
            full_output_path=None,
            started_at=started,
            finished_at=finished,
            timestamps=Timestamps(created_at=utcnow(), updated_at=utcnow()),
        )
        await self._runs.save(run)
        return output

    def _render_items(self, items: list[dict[str, Any]]) -> str:
        if not items:
            return "(nenhum item fornecido — gere um digest generico sobre Python)"
        lines = []
        for i, item in enumerate(items, start=1):
            lines.append(f"- {i}. [{item.get('source', '?')}] {item.get('title', 'sem titulo')}")
            lines.append(f"  url: {item.get('url', '')}")
            summary = (item.get("summary") or "").strip()
            if summary:
                first = summary.splitlines()[0] if summary.splitlines() else summary
                lines.append(f"  summary: {first[:400]}")
        return "\n".join(lines)

    def _parse_output(self, content: str, source_url_ids: list[str]) -> NewsDigestDraft:
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict) or not str(payload.get("texto", "")).strip():
                raise ValueError
            payload.setdefault("source_url_ids", source_url_ids)
            return NewsDigestDraft(**payload)
        except json.JSONDecodeError, ValueError, TypeError:
            return NewsDigestDraft(
                title="Digest Python",
                texto=content,
                source_url_ids=source_url_ids,
            )


__all__ = [
    "NEWS_DIGEST_AGENT",
    "NEWS_DIGEST_PROMPT",
    "NewsDigestAgent",
    "NewsDigestAgentConfig",
    "NewsDigestDraft",
]
