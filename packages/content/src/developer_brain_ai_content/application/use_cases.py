"""Use cases do content: CreateLinkedInDraft, Lista/Get/Enqueue/MarkPublished/Reject."""

from __future__ import annotations

from datetime import datetime

from developer_brain_ai_shared.errors.base import NotFoundError, ValidationError
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow
from developer_brain_ai_shared.pagination import PaginationParams

from developer_brain_ai_content.application.dto import (
    CreateLinkedInDraftInput,
    GenerateLinkedInInput,
    LinkedInDraftOutput,
    ListDraftsOutput,
)
from developer_brain_ai_content.application.ports import LinkedInGenerator
from developer_brain_ai_content.domain.aggregates import ContentDraft, PublicationQueueItem
from developer_brain_ai_content.domain.repositories import (
    ContentDraftRepository,
    PublicationQueueRepository,
)
from developer_brain_ai_content.domain.value_objects import ContentType, DraftStatus, Hashtag


def _draft_to_out(d: ContentDraft) -> LinkedInDraftOutput:
    md = d.metadata or {}
    return LinkedInDraftOutput(
        draft_id=str(d.id),
        title=d.title,
        gancho=md.get("gancho", ""),
        texto=d.body_markdown,
        conclusao=md.get("conclusao", ""),
        pergunta=md.get("pergunta", ""),
        cta=md.get("cta", ""),
        hashtags=[h.display() for h in d.hashtags],
        status=d.status.value,
        created_at=d.timestamps.created_at,
        updated_at=d.timestamps.updated_at,
    )


class CreateLinkedInDraft:
    def __init__(self, drafts: ContentDraftRepository) -> None:
        self._drafts = drafts

    async def execute(
        self, tenant_id: TenantId, data: CreateLinkedInDraftInput
    ) -> LinkedInDraftOutput:
        try:
            hashtags = [Hashtag(h) for h in data.hashtags]
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        now = utcnow()
        draft = ContentDraft(
            id=object(),
            tenant_id=tenant_id,
            agent="linkedin",
            content_type=ContentType.LINKEDIN_POST,
            title=data.title,
            body_markdown=data.texto,
            hashtags=hashtags,
            metadata={
                "gancho": data.gancho,
                "conclusao": data.conclusao,
                "pergunta": data.pergunta,
                "cta": data.cta,
                "source_entry_ids": data.source_entry_ids,
            },
            status=DraftStatus.PENDING_REVIEW,
            timestamps=Timestamps(created_at=now, updated_at=now),
        )
        await self._drafts.save(draft)
        return _draft_to_out(draft)


class GenerateLinkedInDraft:
    """Gera um Draft via LinkedInAgent (ai) e persiste como ContentDraft.

    O agent e injetado como port (LinkedInGenerator); nao persiste por conta
    propria — apenas retorna o conteudo prontinho para virar draft.
    """

    def __init__(self, drafts: ContentDraftRepository, generator: LinkedInGenerator) -> None:
        self._drafts = drafts
        self._generator = generator

    async def execute(
        self, tenant_id: TenantId, data: GenerateLinkedInInput
    ) -> LinkedInDraftOutput:
        result = await self._generator.execute(
            tenant_id,
            entries=data.entries,
            ai_writing_tone=data.ai_writing_tone,
            ai_language=data.ai_language,
        )
        try:
            hashtags = [Hashtag(h) for h in result.hashtags]
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        now = utcnow()
        draft = ContentDraft(
            id=object(),
            tenant_id=tenant_id,
            agent="linkedin",
            content_type=ContentType.LINKEDIN_POST,
            title=result.title,
            body_markdown=result.texto,
            hashtags=hashtags,
            metadata={
                "gancho": result.gancho,
                "conclusao": result.conclusao,
                "pergunta": result.pergunta,
                "cta": result.cta,
                "source_entry_ids": result.source_entry_ids,
            },
            status=DraftStatus.PENDING_REVIEW,
            timestamps=Timestamps(created_at=now, updated_at=now),
        )
        await self._drafts.save(draft)
        return _draft_to_out(draft)


class ListDrafts:
    def __init__(self, drafts: ContentDraftRepository) -> None:
        self._drafts = drafts

    async def execute(
        self,
        tenant_id: TenantId,
        *,
        content_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[ListDraftsOutput]:
        ct = ContentType(content_type) if content_type else None
        st = DraftStatus(status) if status else None
        items = await self._drafts.list(
            tenant_id,
            content_type=ct,
            status=st,
            pagination=PaginationParams(limit=page_size, offset=(page - 1) * page_size),
        )
        return [
            ListDraftsOutput(
                id=str(d.id),
                content_type=d.content_type.value,
                title=d.title,
                status=d.status.value,
                created_at=d.timestamps.created_at,
                updated_at=d.timestamps.updated_at,
            )
            for d in items
        ]


class GetDraft:
    def __init__(self, drafts: ContentDraftRepository) -> None:
        self._drafts = drafts

    async def execute(self, tenant_id: TenantId, draft_id: str) -> LinkedInDraftOutput:
        draft = await self._drafts.get_by_id(tenant_id, draft_id)
        if draft is None:
            raise NotFoundError("draft nao encontrado", details={"id": draft_id})
        return _draft_to_out(draft)


class EnqueueDraft:
    """Marca um draft como queued e cria um PublicationQueueItem com scheduled_for."""

    def __init__(
        self,
        drafts: ContentDraftRepository,
        queue: PublicationQueueRepository,
    ) -> None:
        self._drafts = drafts
        self._queue = queue

    async def execute(
        self, tenant_id: TenantId, draft_id: str, scheduled_for: datetime | None = None
    ) -> None:
        draft = await self._drafts.get_by_id(tenant_id, draft_id)
        if draft is None:
            raise NotFoundError("draft nao encontrado", details={"id": draft_id})
        draft.queue_for_publication()
        await self._drafts.save(draft)
        now = utcnow()
        item = PublicationQueueItem(
            id=object(),
            tenant_id=tenant_id,
            draft_id=draft.id,
            scheduled_for=scheduled_for or now,
            queued_at=now,
            timestamps=Timestamps(created_at=now, updated_at=now),
        )
        await self._queue.enqueue(item)


class MarkPublished:
    def __init__(
        self,
        drafts: ContentDraftRepository,
        queue: PublicationQueueRepository,
    ) -> None:
        self._drafts = drafts
        self._queue = queue

    async def execute(self, tenant_id: TenantId, draft_id: str) -> None:
        draft = await self._drafts.get_by_id(tenant_id, draft_id)
        if draft is None:
            raise NotFoundError("draft nao encontrado", details={"id": draft_id})
        draft.mark_published()
        await self._drafts.save(draft)


class RejectDraft:
    def __init__(self, drafts: ContentDraftRepository) -> None:
        self._drafts = drafts

    async def execute(self, tenant_id: TenantId, draft_id: str, reason: str | None = None) -> None:
        draft = await self._drafts.get_by_id(tenant_id, draft_id)
        if draft is None:
            raise NotFoundError("draft nao encontrado", details={"id": draft_id})
        draft.mark_rejected(reason)
        await self._drafts.save(draft)


__all__ = [
    "CreateLinkedInDraft",
    "EnqueueDraft",
    "GenerateLinkedInDraft",
    "GetDraft",
    "ListDrafts",
    "MarkPublished",
    "RejectDraft",
]
