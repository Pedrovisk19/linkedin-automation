"""Repository interfaces (Ports) do modulo ai."""

from __future__ import annotations

from typing import Protocol

from developer_brain_ai_shared.kernel.id import TenantId

from developer_brain_ai_ai.domain.aggregates import AgentRun, MemoryFragment


class AgentRunRepository(Protocol):
    async def save(self, run: AgentRun) -> None: ...
    async def list_recent(
        self, tenant_id: TenantId, agent: str, limit: int = 50
    ) -> list[AgentRun]: ...


class MemoryFragmentRepository(Protocol):
    async def save(self, fragment: MemoryFragment) -> None: ...
    async def search_similar(
        self,
        tenant_id: TenantId,
        embedding: list[float],
        top_k: int = 6,
        source_module: str | None = None,
    ) -> list[MemoryFragment]: ...
    async def exists_by_key(self, tenant_id: TenantId, key: str) -> bool: ...


__all__ = ["AgentRunRepository", "MemoryFragmentRepository"]
