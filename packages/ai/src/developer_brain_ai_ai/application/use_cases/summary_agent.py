"""SummaryAgent: gera resumo (diario/semanal/mensal) a partir de JournalEntries."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from developer_brain_ai_ai.application.dto import SummaryAgentInput, SummaryAgentOutput
from developer_brain_ai_ai.application.ports import AIProvider, ChatMessage, ChatRequest
from developer_brain_ai_ai.application.prompt_engine import PromptEngine
from developer_brain_ai_ai.domain.aggregates import AgentRun
from developer_brain_ai_ai.domain.repositories import AgentRunRepository
from developer_brain_ai_ai.domain.value_objects import AgentName, PromptName
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow

SUMMARY_AGENT = AgentName("summary")
SUMMARY_PROMPT = PromptName("summary")


@dataclass
class SummaryAgentConfig:
    temperature: float = 0.3
    max_tokens: int = 1500


class SummaryAgent:
    """Gera resumo de periodo a partir de JournalEntries.

    Insumo: SummaryAgentInput com entries (lista de dicts com title/technologies/
    difficulties/learnings/bugs_found/resolutions).
    Saida: SummaryAgentOutput (title + markdown + top_learnings + metrics).
    """

    def __init__(
        self,
        *,
        provider: AIProvider,
        prompt_engine: PromptEngine,
        runs: AgentRunRepository,
        config: SummaryAgentConfig | None = None,
    ) -> None:
        self._provider = provider
        self._engine = prompt_engine
        self._runs = runs
        self._cfg = config or SummaryAgentConfig()

    async def execute(self, tenant_id: TenantId, data: SummaryAgentInput) -> SummaryAgentOutput:
        tpl = self._engine.load(SUMMARY_PROMPT)
        entries_blob = self._render_entries(data.entries)
        rendered_system = tpl.render(
            {
                "period_kind": data.period_kind,
                "start_date": str(data.start_date),
                "end_date": str(data.end_date),
                "entries_blob": entries_blob,
                "ai_language": "pt-BR",
            }
        )

        request = ChatRequest(
            messages=[
                ChatMessage(role="system", content=rendered_system),
                ChatMessage(role="user", content=self._user_instruction(data)),
            ],
            temperature=self._cfg.temperature,
            max_tokens=self._cfg.max_tokens,
            response_format=SummaryAgentOutput,
        )

        started = datetime.now(UTC)
        response = await self._provider.chat(request)
        finished = datetime.now(UTC)

        output = self._parse_output(response.content, data)

        inputs_hash = hashlib.sha256(
            json.dumps({"entries": data.entries, "period": data.period_kind}, default=str).encode()
        ).hexdigest()

        run = AgentRun(
            id=object(),
            tenant_id=tenant_id,
            agent=SUMMARY_AGENT,
            prompt_name=SUMMARY_PROMPT,
            prompt_version=tpl.version,
            inputs_hash=inputs_hash,
            output_summary=output.title,
            full_output_path=None,
            started_at=started,
            finished_at=finished,
            timestamps=Timestamps(created_at=utcnow(), updated_at=utcnow()),
        )
        await self._runs.save(run)
        return output

    def _render_entries(self, entries: list[dict]) -> str:
        if not entries:
            return "(nenhum registro neste periodo)"
        lines = []
        for i, e in enumerate(entries, start=1):
            lines.append(
                f"- {i}. {e.get('title','sem titulo')} ({e.get('entry_date','?')}) | "
                f"tech={','.join(e.get('technologies',[]))} | "
                f"minutos={e.get('study_minutes',0)}"
            )
            if e.get("learnings"):
                lines.append(f"  learnings: {e['learnings'][:300]}")
            if e.get("difficulties"):
                lines.append(f"  difficulties: {e['difficulties'][:200]}")
            if e.get("bugs_found"):
                lines.append(f"  bugs: {len(e['bugs_found'])}")
        return "\n".join(lines)

    def _user_instruction(self, data: SummaryAgentInput) -> str:
        return (
            f"Gere um resumo {data.period_kind} para o periodo "
            f"{data.start_date} a {data.end_date} com base nos diarios fornecidos. "
            "Responda em UTF-8 em Markdown, sem emojis extra, listando os principais "
            "aprendizados, dificuldades superadas, tecnologias que evoluiu e metricas "
            f"(horas estudadas, posts gerados, commits). Total de entradas: {len(data.entries)}."
        )

    def _parse_output(self, content: str, data: SummaryAgentInput) -> SummaryAgentOutput:
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ValueError
            payload.setdefault("period_kind", data.period_kind)
            payload.setdefault("start_date", data.start_date.isoformat())
            payload.setdefault("end_date", data.end_date.isoformat())
            payload.setdefault("top_learnings", [])
            payload.setdefault("metrics", {})
            payload.setdefault("title", f"Resumo {data.period_kind} {data.start_date}")
            payload.setdefault("markdown", content)
            return SummaryAgentOutput(**payload)
        except (json.JSONDecodeError, ValueError, TypeError):
            return SummaryAgentOutput(
                period_kind=data.period_kind,
                start_date=data.start_date,
                end_date=data.end_date,
                title=f"Resumo {data.period_kind} {data.start_date}",
                markdown=content,
                top_learnings=[],
                metrics={},
            )


__all__ = ["SummaryAgent", "SummaryAgentConfig", "SUMMARY_AGENT", "SUMMARY_PROMPT"]