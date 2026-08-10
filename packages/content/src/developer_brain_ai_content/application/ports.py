"""Ports do content: colaboradores injetados sem acoplamento a infra."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from developer_brain_ai_shared.kernel.id import TenantId

if TYPE_CHECKING:
    from developer_brain_ai_ai.application.use_cases import LinkedInDraft


class LinkedInGenerator(Protocol):
    """Gerador de drafts de LinkedIn (implementado por LinkedInAgent)."""

    async def execute(
        self,
        tenant_id: TenantId,
        *,
        entries: list[dict],
        ai_writing_tone: str = ...,
        ai_language: str = ...,
    ) -> LinkedInDraft: ...


__all__ = ["LinkedInGenerator"]
