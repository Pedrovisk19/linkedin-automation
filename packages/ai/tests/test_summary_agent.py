"""Testes do SummaryAgent com FakeAIProvider + FakeAgentRunRepository."""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

from ai_fakes import FakeAgentRunRepository, FakeAIProvider
from developer_brain_ai_ai.application.dto import SummaryAgentInput
from developer_brain_ai_ai.application.prompt_engine import PromptEngine
from developer_brain_ai_ai.application.use_cases import SummaryAgent, SummaryAgentConfig
from developer_brain_ai_shared.kernel.id import TenantId

PROMPTS = Path(__file__).resolve().parents[3] / "prompts"


def _entries() -> list[dict]:
    return [
        {
            "title": "Estudei FastAPI",
            "entry_date": "2026-08-06",
            "study_minutes": 90,
            "technologies": ["fastapi"],
            "learnings": "dependency injection é otimo",
            "difficulties": "entender testclient",
            "bugs_found": ["typo em router"],
            "resolutions": ["removi from future"],
        },
        {
            "title": "Estudei SQLAlchemy 2",
            "entry_date": "2026-08-07",
            "study_minutes": 60,
            "technologies": ["sqlalchemy"],
            "learnings": "async session factory",
            "difficulties": "",
            "bugs_found": [],
            "resolutions": [],
        },
    ]


def test_summary_agent_returns_output_from_provider() -> None:
    provider = FakeAIProvider(
        chat_response=json.dumps(
            {
                "title": "Resumo semanal 2026-W32",
                "markdown": "# R\n aprendi fastapi",
                "top_learnings": ["DI", "async session"],
                "metrics": {"hours": 2, "entries": 2},
                "period_kind": "weekly",
                "start_date": "2026-08-01",
                "end_date": "2026-08-07",
            }
        )
    )
    runs = FakeAgentRunRepository()
    agent = SummaryAgent(provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=runs)

    out = asyncio.run(
        agent.execute(
            TenantId.new(),
            SummaryAgentInput(
                period_kind="weekly",
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 7),
                entries=_entries(),
            ),
        )
    )
    assert out.title == "Resumo semanal 2026-W32"
    assert "fastapi" in out.markdown
    assert out.top_learnings == ["DI", "async session"]
    assert out.metrics == {"hours": 2, "entries": 2}


def test_summary_agent_persists_agent_run_with_version_hash() -> None:
    provider = FakeAIProvider(
        chat_response='{"title":"x","markdown":"y","top_learnings":[],"metrics":{}}'
    )
    runs = FakeAgentRunRepository()
    agent = SummaryAgent(provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=runs)

    asyncio.run(
        agent.execute(
            TenantId.new(),
            SummaryAgentInput(
                period_kind="daily",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
                entries=[{"title": "x", "study_minutes": 30}],
            ),
        )
    )
    assert len(runs.saved) == 1
    run = runs.saved[0]
    assert run.agent.value == "summary"
    assert run.prompt_name.value == "summary"
    assert len(run.prompt_version.value) == 64
    assert run.inputs_hash
    assert run.finished_at >= run.started_at
    assert run.output_summary == "x"


def test_summary_agent_handles_invalid_json_gracefully() -> None:
    provider = FakeAIProvider(chat_response="not-a-json-but-markdown-**bold**")
    runs = FakeAgentRunRepository()
    agent = SummaryAgent(provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=runs)

    out = asyncio.run(
        agent.execute(
            TenantId.new(),
            SummaryAgentInput(
                period_kind="monthly",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                entries=[],
            ),
        )
    )
    assert out.period_kind == "monthly"
    assert "markdown-but" in out.markdown or "bold" in out.markdown
    assert out.top_learnings == []


def test_summary_agent_sends_system_prompt_with_template_variables() -> None:
    provider = FakeAIProvider(chat_response='{"title":"ok"}')
    runs = FakeAgentRunRepository()
    agent = SummaryAgent(provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=runs)
    asyncio.run(
        agent.execute(
            TenantId.new(),
            SummaryAgentInput(
                period_kind="weekly",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 7),
                entries=_entries(),
            ),
        )
    )
    assert provider.last_request is not None
    assert len(provider.last_request.messages) == 2
    system = provider.last_request.messages[0]
    assert system.role == "system"
    assert "weekly" in system.content
    assert "2026-01-01" in system.content
    assert "2026-01-07" in system.content
    assert "Estudei FastAPI" in system.content


def test_summary_agent_passes_temperature_and_max_tokens() -> None:
    provider = FakeAIProvider(chat_response='{"title":"ok"}')
    runs = FakeAgentRunRepository()
    cfg = SummaryAgentConfig(temperature=0.1, max_tokens=250)
    agent = SummaryAgent(
        provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=runs, config=cfg
    )
    asyncio.run(
        agent.execute(
            TenantId.new(),
            SummaryAgentInput(
                period_kind="daily",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
                entries=[],
            ),
        )
    )
    assert provider.last_request.temperature == 0.1
    assert provider.last_request.max_tokens == 250


def test_summary_agent_with_empty_entries_produces_blob_placeholder() -> None:
    provider = FakeAIProvider(chat_response='{"title":"x"}')
    runs = FakeAgentRunRepository()
    agent = SummaryAgent(provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=runs)
    asyncio.run(
        agent.execute(
            TenantId.new(),
            SummaryAgentInput(
                period_kind="daily",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
                entries=[],
            ),
        )
    )
    assert "nenhum registro" in provider.last_request.messages[0].content
