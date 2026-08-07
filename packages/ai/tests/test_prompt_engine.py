"""Testes do PromptEngine: le prompts/*.md reais, cache, render variaveis."""
from __future__ import annotations

import pytest

from developer_brain_ai_ai.application.prompt_engine import PromptEngine, PromptNotFound
from developer_brain_ai_ai.domain import PromptName
from developer_brain_ai_ai.domain.aggregates import PromptTemplate
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "prompts"


def test_load_summary_prompt_returns_template_with_template_content() -> None:
    engine = PromptEngine(ROOT)
    tpl = engine.load(PromptName("summary"))
    assert isinstance(tpl, PromptTemplate)
    assert tpl.prompt_name.value == "summary"
    assert "Summary Agent" in tpl.content or "resumos" in tpl.content.lower()
    assert len(tpl.version.value) == 64


def test_load_linkedin_prompt_returns_template() -> None:
    tpl = PromptEngine(ROOT).load(PromptName("linkedin"))
    assert "LinkedIn" in tpl.content or "linkedin" in tpl.content.lower()


def test_load_missing_prompt_raises_prompt_not_found() -> None:
    with pytest.raises(PromptNotFound):
        PromptEngine(Path("/nonexistent/xyz")).load(PromptName("nope"))


def test_engine_caches_content_across_loads() -> None:
    engine = PromptEngine(ROOT)
    a = engine.load(PromptName("summary"))
    b = engine.load(PromptName("summary"))
    assert a is b  # cacheado


def test_refresh_reloads_after_cache_clear() -> None:
    engine = PromptEngine(ROOT)
    a = engine.load(PromptName("summary"))
    b = engine.refresh(PromptName("summary"))
    assert a is not b


def test_render_substitutes_summary_variables() -> None:
    tpl = PromptEngine(ROOT).load(PromptName("summary"))
    rendered = tpl.render({"period_kind": "weekly", "start_date": "2026-01-01", "end_date": "2026-01-07", "entries_blob": "blob", "ai_language": "pt-BR"})
    assert "weekly" in rendered
    assert "2026-01-01" in rendered