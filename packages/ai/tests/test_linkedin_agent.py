"""Testes do LinkedInAgent no modulo ai."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ai_fakes import FakeAgentRunRepository, FakeAIProvider
from developer_brain_ai_ai.application.prompt_engine import PromptEngine
from developer_brain_ai_ai.application.use_cases import LinkedInAgent
from developer_brain_ai_shared.kernel.id import TenantId

PROMPTS = Path(__file__).resolve().parents[3] / "prompts"


def _entries() -> list[dict]:
    return [
        {
            "id": "abc-1",
            "title": "Estudei Clean Architecture",
            "entry_date": "2026-08-06",
            "study_minutes": 90,
            "technologies": ["fastapi", "pydantic"],
            "learnings": "separar camadas é libertador",
            "difficulties": "import cycle no comeco",
            "bugs_found": ["cycle kernel->events"],
            "resolutions": ["TYPE_CHECKING fixou"],
        }
    ]


def test_linkedin_returns_structured_output_when_json() -> None:
    out_json = json.dumps(
        {
            "title": "DI mudou meu jeito",
            "gancho": "Voce ja separou camadas?",
            "texto": "# body",
            "conclusao": "separacao paga dividendos",
            "pergunta": "qual a sua camada favorita?",
            "cta": "comenta",
            "hashtags": ["#FastAPI", "Python"],
        }
    )
    provider = FakeAIProvider(chat_response=out_json)
    runs = FakeAgentRunRepository()
    agent = LinkedInAgent(provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=runs)

    out = asyncio.run(agent.execute(TenantId.new(), entries=_entries()))
    assert out.title == "DI mudou meu jeito"
    assert "fastapi" in out.hashtags
    assert "python" in out.hashtags
    assert out.cta == "comenta"
    assert "abc-1" in out.source_entry_ids


def test_linkedin_fallback_to_markdown_when_response_not_json() -> None:
    provider = FakeAIProvider(chat_response="** este não é JSON **")
    agent = LinkedInAgent(
        provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=FakeAgentRunRepository()
    )
    out = asyncio.run(agent.execute(TenantId.new(), entries=_entries()))
    assert out.title == "Post gerado"
    assert out.texto.startswith("** este")
    assert "abc-1" in out.source_entry_ids


def test_linkedin_sends_system_prompt_with_template_variables() -> None:
    provider = FakeAIProvider(chat_response="{}")
    agent = LinkedInAgent(
        provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=FakeAgentRunRepository()
    )
    asyncio.run(
        agent.execute(
            TenantId.new(),
            entries=_entries(),
            ai_writing_tone="dev-compartilhando-evolucao",
            ai_language="pt-BR",
        )
    )
    sys_msg = provider.last_request.messages[0].content
    assert "dev-compartilhando-evolucao" in sys_msg
    assert "pt-BR" in sys_msg
    assert "Estudei Clean Architecture" in sys_msg


def test_linkedin_persists_agent_run_with_summary() -> None:
    provider = FakeAIProvider(chat_response="{}")
    runs = FakeAgentRunRepository()
    agent = LinkedInAgent(provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=runs)
    asyncio.run(agent.execute(TenantId.new(), entries=_entries()))
    assert len(runs.saved) == 1
    run = runs.saved[0]
    assert run.agent.value == "linkedin"
    assert run.prompt_name.value == "linkedin"
    assert len(run.prompt_version.value) == 64


def test_linkedin_empty_entries_emits_placeholder_in_prompt() -> None:
    provider = FakeAIProvider(chat_response="{}")
    agent = LinkedInAgent(
        provider=provider, prompt_engine=PromptEngine(PROMPTS), runs=FakeAgentRunRepository()
    )
    asyncio.run(agent.execute(TenantId.new(), entries=[]))
    assert "nenhum diario" in provider.last_request.messages[0].content


def test_linkedin_passes_temperature_max_tokens_from_config() -> None:
    from developer_brain_ai_ai.application.use_cases import LinkedInAgentConfig

    provider = FakeAIProvider(chat_response="{}")
    agent = LinkedInAgent(
        provider=provider,
        prompt_engine=PromptEngine(PROMPTS),
        runs=FakeAgentRunRepository(),
        config=LinkedInAgentConfig(temperature=0.7, max_tokens=222),
    )
    asyncio.run(agent.execute(TenantId.new(), entries=_entries()))
    assert provider.last_request.temperature == 0.7
    assert provider.last_request.max_tokens == 222
