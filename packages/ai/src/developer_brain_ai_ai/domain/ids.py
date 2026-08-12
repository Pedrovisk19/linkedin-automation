"""IDs tipados do modulo ai (PromptTemplate/AgentRun/MemoryFragment)."""

from developer_brain_ai_shared.kernel.id import TypedId


class PromptTemplateId(TypedId["PromptTemplateId"]):
    """Identificador de PromptTemplate (snapshot de prompt)."""


class AgentRunId(TypedId["AgentRunId"]):
    """Identificador de AgentRun (execucao de agente)."""


class MemoryFragmentId(TypedId["MemoryFragmentId"]):
    """Identificador de MemoryFragment (contexto persistido)."""


__all__ = ["AgentRunId", "MemoryFragmentId", "PromptTemplateId"]
