"""LinkedInAgent: gera LinkedInDraft (title+gancho+texto+conclusao+pergunta+
hashtags+cta) a partir de JournalEntries.

Nao persiste — apenas retorna a output. Persistir em ContentDraft e responsabilidade
do composition root (em Fase 7 via modulo automation). Mantem o agente isolado e
testavel contra FakeAIProvider sem depender do modulo content.
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

from developer_brain_ai_ai.application.dto import SummaryAgentOutput  # noqa: F401
from developer_brain_ai_ai.application.ports import AIProvider, ChatMessage, ChatRequest
from developer_brain_ai_ai.application.prompt_engine import PromptEngine
from developer_brain_ai_ai.domain.aggregates import AgentRun
from developer_brain_ai_ai.domain.ids import AgentRunId
from developer_brain_ai_ai.domain.repositories import AgentRunRepository
from developer_brain_ai_ai.domain.value_objects import AgentName, PromptName

LINKEDIN_AGENT = AgentName("linkedin")
LINKEDIN_PROMPT = PromptName("linkedin")


_TAG_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{1,49}$")


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
            if _TAG_RE.match(v):
                tags.append(v)
        data["hashtags"] = tags
        super().__init__(**data)


@dataclass
class LinkedInAgentConfig:
    temperature: float = 0.6
    max_tokens: int = 8192


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
        entries: list[dict[str, Any]],
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
            id=AgentRunId.new(),
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

    def _render_entries(self, entries: list[dict[str, Any]]) -> str:
        if not entries:
            return (
                "(nenhum diario fornecido — gere um post generico sobre o por que"
                " compartilhar evolucao)"
            )
        lines = []
        for i, e in enumerate(entries, start=1):
            lines.append(
                f"- {i}. {e.get('title', 'sem titulo')} ({e.get('entry_date', '?')}) "
                f"| tech={','.join(e.get('technologies', []))} | "
                f"minutos={e.get('study_minutes', 0)}"
            )
            if e.get("learnings"):
                lines.append(f"  learnings: {e['learnings']}")
            if e.get("difficulties"):
                lines.append(f"  difficulties: {e['difficulties']}")
            if e.get("bugs_found"):
                lines.append(f"  bugs: {len(e['bugs_found'])}")
                for b in e.get("bugs_found", [])[:5]:
                    if isinstance(b, dict):
                        lines.append(f"    - {b.get('title', '')}: {b.get('resolution', '')}")
            if e.get("resolutions"):
                lines.append(f"  resolutions: {e['resolutions']}")
        return "\n".join(lines)

    def _parse_output(self, content: str, entries: list[dict[str, Any]]) -> LinkedInDraft:
        payload = self._extract_json_object(content)
        if payload is not None and str(payload.get("texto", "")).strip():
            payload.setdefault(
                "source_entry_ids", [e.get("id", "") for e in entries if e.get("id")]
            )
            return LinkedInDraft(**payload)
        return LinkedInDraft(
            title="Post gerado",
            texto=content,
            source_entry_ids=[e.get("id", "") for e in entries if e.get("id")],
        )

    @staticmethod
    def _sanitize_json_control_chars(content: str) -> str:
        """Escapa quebras de linha/tab literais dentro de strings de JSON.

        LLMs costumam emitir newlines reais no valor de ``texto`` (tipicamente
        dentro de code fences) em vez de ``\\n``, o que torna o JSON invalido.
        Repara preservando a estrutura: fora de strings nada muda.
        """
        out: list[str] = []
        in_string = False
        escaped = False
        for ch in content:
            if in_string and not escaped and ch in ("\n", "\r", "\t"):
                out.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[ch])
                continue
            out.append(ch)
            if escaped:
                escaped = False
            elif in_string and ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = not in_string
        return "".join(out)

    @staticmethod
    def _extract_json_object(content: str) -> dict[str, Any] | None:  # noqa: PLR0912
        """Extrai um JSON object de resposta LLM tolerando code fences e texto ao redor.

        - Remove code fences ```json ... ``` ou ``` ... ```
        - Repara newlines literais dentro de strings (falha comum de LLM)
        - Localiza o primeiro ``{`` ate o ultimo ``}`` e tenta ``json.loads``
        - Retorna ``None`` se nao encontrar JSON valido
        """
        text = LinkedInAgent._sanitize_json_control_chars(content).strip()
        # Remove code fences ```json ... ``` ou ``` ... ```
        if text.startswith("```"):
            # descarta a primeira linha (```json ou ```)
            lines = text.splitlines()
            if len(lines) >= 2:
                lines = lines[1:]
            # remove fence final se existir
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        # Tentativa direta
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
        # Fallback: extrair substring entre { e } (usando balanceamento de chaves)
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        end = -1
        for i, ch in enumerate(text[start:], start=start):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            return None
        try:
            parsed = json.loads(text[start:end])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


__all__ = [
    "LINKEDIN_AGENT",
    "LINKEDIN_PROMPT",
    "LinkedInAgent",
    "LinkedInAgentConfig",
    "LinkedInDraft",
]
