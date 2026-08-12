"""Agregado PromptTemplate e AgentRun.

- PromptTemplate: snapshot declarado em prompts/*.md, identificado por nome+version.
  Cacheavel. Nao persistido (lido do FS na hot path) — versao persistida apenas em
  AgentRun para reprodutibilidade.
- AgentRun: execucao de um agente (tenant, agent, prompt_version, inputs_hash,
  output_summary, full_output_path opcional). Persistida p/ auditoria.
- MemoryFragment: trecho persistido (content + embedding) p/ contexto anti-repeticao.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_ai.domain.renderer import render
from developer_brain_ai_ai.domain.value_objects import AgentName, PromptName, PromptVersion


@dataclass(eq=False)
class PromptTemplate(AggregateRoot):
    """Snapshot imutavel de um prompt. ``content`` e o template bruto."""

    prompt_name: PromptName
    version: PromptVersion
    content: str

    def render(self, variables: dict[str, str]) -> str:

        return render(self.content, variables)


@dataclass(eq=False)
class AgentRun(AggregateRoot):
    tenant_id: TenantId
    agent: AgentName
    prompt_name: PromptName
    prompt_version: PromptVersion
    inputs_hash: str
    output_summary: str
    full_output_path: str | None
    started_at: datetime
    finished_at: datetime
    timestamps: Timestamps


@dataclass(eq=False)
class MemoryFragment(AggregateRoot):
    """Fragmento persistido de contexto. Embedding fica em infra (pgvector)."""

    tenant_id: TenantId
    key: str
    content: str
    source_module: str
    timestamps: Timestamps
    embedding: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.key or not self.key.strip():
            raise ValueError("memory fragment key nao pode ser vazio")
        if not self.content or not self.content.strip():
            raise ValueError("memory fragment content nao pode ser vazio")
        if len(self.key) > 120:
            raise ValueError("memory fragment key excede 120 chars")
        if len(self.source_module) > 40:
            raise ValueError("source_module excede 40 chars")


__all__ = ["AgentRun", "MemoryFragment", "PromptTemplate"]
