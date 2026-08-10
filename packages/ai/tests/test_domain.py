"""Testes do dominio e ports do ai."""

from __future__ import annotations

import pytest
from developer_brain_ai_ai.domain import (
    AgentName,
    MemoryFragment,
    PromptName,
    PromptTemplate,
    PromptVersion,
    render,
)
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow


def test_prompt_name_normalizes_and_validates() -> None:
    assert str(PromptName("  Linkedin ")) == "linkedin"
    assert str(PromptName("summary_v2")) == "summary_v2"
    for bad in ["", "x" * 41, "with space", "weird!"]:
        with pytest.raises(ValueError):
            PromptName(bad)


def test_agent_name_validates() -> None:
    assert str(AgentName("Summary")) == "summary"
    with pytest.raises(ValueError):
        AgentName("")
    with pytest.raises(ValueError):
        AgentName("x" * 41)


def test_prompt_version_from_content_is_sha256() -> None:
    v = PromptVersion.from_content("hello")
    assert len(v.value) == 64
    assert PromptVersion.from_content("hello") == v
    assert PromptVersion.from_content("hello2") != v


def test_prompt_version_rejects_wrong_length() -> None:
    with pytest.raises(ValueError):
        PromptVersion("abc")


def test_render_substitutes_variables() -> None:
    out = render("ola {{name}}!", {"name": "mundo"})
    assert out == "ola mundo!"


def test_render_keeps_unknown_keys_literally() -> None:
    out = render("ola {{unknown}}!", {"name": "mundo"})
    assert out == "ola {{unknown}}!"


def test_prompt_template_render_works() -> None:
    tpl = PromptTemplate(
        id=object(),
        prompt_name=PromptName("x"),
        version=PromptVersion.from_content("oi {{name}}"),
        content="oi {{name}}",
    )
    assert tpl.render({"name": "mundo"}) == "oi mundo"


def test_memory_fragment_rejects_empty_key_or_content() -> None:
    now = utcnow()
    base_ts = Timestamps(created_at=now, updated_at=now)
    with pytest.raises(ValueError):
        MemoryFragment(
            id=object(),
            tenant_id=TenantId.new(),
            key="",
            content="ok",
            source_module="journal",
            timestamps=base_ts,
        )
    with pytest.raises(ValueError):
        MemoryFragment(
            id=object(),
            tenant_id=TenantId.new(),
            key="k",
            content="",
            source_module="journal",
            timestamps=base_ts,
        )


def test_memory_fragment_rejects_too_long_key() -> None:
    now = utcnow()
    with pytest.raises(ValueError):
        MemoryFragment(
            id=object(),
            tenant_id=TenantId.new(),
            key="x" * 121,
            content="ok",
            source_module="journal",
            timestamps=Timestamps(created_at=now, updated_at=now),
        )
