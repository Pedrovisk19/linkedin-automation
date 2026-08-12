"""Ports do content: colaboradores injetados sem acoplamento a infra."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from developer_brain_ai_shared.kernel.id import TenantId

if TYPE_CHECKING:
    from developer_brain_ai_ai.application.use_cases import LinkedInDraft


class LinkedInGenerator(Protocol):
    """Gerador de drafts de LinkedIn (implementado por LinkedInAgent)."""

    async def execute(
        self,
        tenant_id: TenantId,
        *,
        entries: list[dict[str, Any]],
        ai_writing_tone: str = ...,
        ai_language: str = ...,
    ) -> LinkedInDraft: ...


class LinkedInPostPublisher(Protocol):
    """Publica um post no LinkedIn e devolve a URN criada (implementado em integrations)."""

    async def publish(
        self,
        tenant_id: TenantId,
        *,
        text: str,
        hashtags: list[str],
    ) -> str: ...


__all__ = ["LinkedInGenerator", "LinkedInPostPublisher"]
