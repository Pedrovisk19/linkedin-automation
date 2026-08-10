"""LinkedInAgent: gera LinkedInDraft (title+gancho+texto+conclusao+pergunta+
hashtags+cta) a partir de JournalEntries.

Nao persiste — apenas retorna a output. Persistir em ContentDraft e responsabilidade
do composition root (em Fase 7 via modulo automation). Mantem o agente isolado e
testavel contra FakeAIProvider sem depender do modulo content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow
from pydantic import BaseModel, Field

from developer_brain_ai_ai.application.dto import SummaryAgentOutput  # noqa: F401
from developer_brain_ai_ai.application.ports import AIProvider, ChatMessage, ChatRequest
from developer_brain_ai_ai.application.prompt_engine import PromptEngine
from developer_brain_ai_ai.domain.aggregates import AgentRun
from developer_brain_ai_ai.domain.repositories import AgentRunRepository
from developer_brain_ai_ai.domain.value_objects import AgentName, PromptName

LINKEDIN_AGENT = AgentName("linkedin")
LINKEDIN_PROMPT = PromptName("linkedin")


class LinkedInDraft(BaseModel):
    """Output bruto do agent. Hashtags normalizadas (sem # e lowercase)."""

    title: str = Field(default="")
    gancho: str = Field(default="")
    texto: str = Field(default="")
    conclusao: str = Field(default="")
    pergunta: str = Field(default="")
    cta: str = Field(default="")
    hashtags: list[str] = Field(default_factory=list)
    source_entry_ids: list[str] = Field(default_factory=list)

    @classmethod
    def _normalize_tag(cls, raw: str) -> str:
        v = raw.strip()
        if v.startswith("#"):
            v = v[1:]
        return v.lower()

    def __init__(self, **data):  # type: ignore[no-untyped-def]
        raw_tags = data.get("hashtags") or []
        data["hashtags"] = [
            self._normalize_tag(t) for t in raw_tags if isinstance(t, str) and t.strip()
        ]
        super().__init__(**data)


@dataclass
class LinkedInAgentConfig:
    temperature: float = 0.6
    max_tokens: int = 1500


class LinkedInAgent:
    def __init__(
        self,
        *,
        provider: AIProvider,
        prompt_engine: PromptEngine,
        runs: AgentRunRepository,
        config: LinkedInAgentConfig | None = None,
    ) -> None:
        self._provider = provider
        self._engine = prompt_engine
        self._runs = runs
        self._cfg = config or LinkedInAgentConfig()

    async def execute(
        self,
        tenant_id: TenantId,
        *,
        entries: list[dict],
        ai_writing_tone: str = "desenvolvedor-compartilhando-evolucao",
        ai_language: str = "pt-BR",
    ) -> LinkedInDraft:
        tpl = self._engine.load(LINKEDIN_PROMPT)
        rendered_system = tpl.render(
            {
                "ai_writing_tone": ai_writing_tone,
                "ai_language": ai_language,
                "entries_blob": self._render_entries(entries),
            }
        )
        request = ChatRequest(
            messages=[
                ChatMessage(role="system", content=rendered_system),
                ChatMessage(
                    role="user",
                    content=(
                        "Gere um post de LinkedIn estruturado (title, gancho, texto, "
                        "conclusao, pergunta, cta, hashtags). Baseie-se SOMENTE nos "
                        "diarios fornecidos. Responda em JSON com as chaves title, "
                        "gancho, texto, conclusao, pergunta, cta, hashtags."
                    ),
                ),
            ],
            temperature=self._cfg.temperature,
            max_tokens=self._cfg.max_tokens,
            response_format=LinkedInDraft,
        )
        started = datetime.now(UTC)
        response = await self._provider.chat(request)
        finished = datetime.now(UTC)

        output = self._parse_output(response.content, entries)

        inputs_hash = hashlib.sha256(
            json.dumps({"entries": entries}, default=str).encode()
        ).hexdigest()
        run = AgentRun(
            id=object(),
            tenant_id=tenant_id,
            agent=LINKEDIN_AGENT,
            prompt_name=LINKEDIN_PROMPT,
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

    def _render_entries(self, entries: list[dict]) -> str:
        if not entries:
            return "(nenhum diario fornecido — gere um post generico sobre o por que compartilhar evolucao)"
        lines = []
        for i, e in enumerate(entries, start=1):
            lines.append(
                f"- {i}. {e.get('title', 'sem titulo')} ({e.get('entry_date', '?')}) "
                f"| tech={','.join(e.get('technologies', []))} | "
                f"minutos={e.get('study_minutes', 0)}"
            )
            if e.get("learnings"):
                lines.append(f"  learnings: {e['learnings'][:300]}")
            if e.get("difficulties"):
                lines.append(f"  difficulties: {e['difficulties'][:200]}")
            if e.get("bugs_found"):
                lines.append(f"  bugs: {len(e['bugs_found'])}")
        return "\n".join(lines)

    def _parse_output(self, content: str, entries: list[dict]) -> LinkedInDraft:
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ValueError
            payload.setdefault(
                "source_entry_ids", [e.get("id", "") for e in entries if e.get("id")]
            )
            return LinkedInDraft(**payload)
        except json.JSONDecodeError, ValueError, TypeError:
            return LinkedInDraft(
                title="Post gerado",
                texto=content,
                source_entry_ids=[e.get("id", "") for e in entries if e.get("id")],
            )


__all__ = [
    "LINKEDIN_AGENT",
    "LINKEDIN_PROMPT",
    "LinkedInAgent",
    "LinkedInAgentConfig",
    "LinkedInDraft",
]
