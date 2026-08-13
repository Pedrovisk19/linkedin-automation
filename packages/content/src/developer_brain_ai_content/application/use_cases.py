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
from developer_brain_ai_content.application.ports import (
    LinkedInGenerator,
    LinkedInPostPublisher,
)
from developer_brain_ai_content.domain.aggregates import ContentDraft, PublicationQueueItem
from developer_brain_ai_content.domain.ids import ContentDraftId, PublicationQueueItemId
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
            id=ContentDraftId.new(),
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
        if not result.texto.strip():
            raise ValidationError("IA retornou corpo de post vazio; tente novamente")

        now = utcnow()
        draft = ContentDraft(
            id=ContentDraftId.new(),
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
            id=PublicationQueueItemId.new(),
            tenant_id=tenant_id,
            draft_id=draft.id,
            scheduled_for=scheduled_for or now,
            queued_at=now,
            timestamps=Timestamps(created_at=now, updated_at=now),
        )
        await self._queue.enqueue(item)


class MarkPublished:
    """Marca um draft como publicado.

    Se um ``LinkedInPostPublisher`` for injetado, publica no LinkedIn ANTES de
    marcar como publicado — se o LinkedIn falhar (nao conectado, token invalido),
    o erro propaga e o draft permanece ``queued`` para retry.
    """

    def __init__(
        self,
        drafts: ContentDraftRepository,
        queue: PublicationQueueRepository,
        publisher: LinkedInPostPublisher | None = None,
    ) -> None:
        self._drafts = drafts
        self._queue = queue
        self._publisher = publisher

    async def execute(self, tenant_id: TenantId, draft_id: str) -> dict[str, str]:
        draft = await self._drafts.get_by_id(tenant_id, draft_id)
        if draft is None:
            raise NotFoundError("draft nao encontrado", details={"id": draft_id})

        post_urn: str | None = None
        if self._publisher is not None:
            post_urn = await self._publisher.publish(
                tenant_id,
                text=draft.body_markdown,
                hashtags=[h.display() for h in draft.hashtags],
            )

        draft.mark_published()
        await self._drafts.save(draft)
        return {"status": "published", "linkedin_post_urn": post_urn or ""}


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
