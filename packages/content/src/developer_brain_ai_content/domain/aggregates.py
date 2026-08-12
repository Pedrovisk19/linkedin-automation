"""Agregado ContentDraft (raiz) + PublicationQueueItem.

- ContentDraft: saida gerada por um agente (tenant, content_type, payload markdown,
  hashtags, status). Imutavel apos criacao exceto por transicoes de estado explicitas.
- PublicationQueueItem: simplesmente registra intent de publicar um draft em ordem
  (tenant_id + draft_id + scheduled_for). Quando publicada, marca draft como published.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from developer_brain_ai_shared.errors.base import ValidationError
from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow

from developer_brain_ai_content.domain.ids import ContentDraftId, PublicationQueueItemId
from developer_brain_ai_content.domain.value_objects import ContentType, DraftStatus, Hashtag


@dataclass(eq=False)
class ContentDraft(AggregateRoot):
    id: ContentDraftId
    tenant_id: TenantId
    agent: str
    content_type: ContentType
    title: str
    body_markdown: str
    hashtags: list[Hashtag] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    status: DraftStatus = DraftStatus.PENDING_REVIEW
    timestamps: Timestamps = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError("title nao pode ser vazio")
        if len(self.title) > 200:
            raise ValueError("title excede 200 chars")
        if not self.body_markdown or not self.body_markdown.strip():
            raise ValueError("body_markdown nao pode ser vazio")
        if len(self.body_markdown) > 20_000:
            raise ValueError("body_markdown excede 20k chars")
        if not isinstance(self.content_type, ContentType):
            raise TypeError("content_type deve ser ContentType")
        if not isinstance(self.status, DraftStatus):
            raise TypeError("status deve ser DraftStatus")
        object.__setattr__(self, "hashtags", _dedupe_hashtags(self.hashtags))
        if self.timestamps is None:
            now = utcnow()
            object.__setattr__(self, "timestamps", Timestamps(created_at=now, updated_at=now))

    def queue_for_publication(self) -> None:
        if self.status != DraftStatus.PENDING_REVIEW:
            raise ValidationError(
                "draft ja em fila/publicado/rejeitado",
                details={"status": self.status.value},
            )
        object.__setattr__(self, "status", DraftStatus.QUEUED)
        _touch(self)

    def mark_published(self) -> None:
        if self.status != DraftStatus.QUEUED:
            raise ValidationError("draft precisa estar queued antes de published")
        object.__setattr__(self, "status", DraftStatus.PUBLISHED)
        _touch(self)

    def mark_rejected(self, _: str | None = None) -> None:
        if self.status in (DraftStatus.PUBLISHED,):
            raise ValidationError("draft publicado nao pode ser rejeitado")
        object.__setattr__(self, "status", DraftStatus.REJECTED)
        _touch(self)


@dataclass(eq=False)
class PublicationQueueItem(AggregateRoot):
    id: PublicationQueueItemId
    tenant_id: TenantId
    draft_id: ContentDraftId
    scheduled_for: datetime
    queued_at: datetime
    published_at: datetime | None = None
    timestamps: Timestamps = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:

        if self.timestamps is None:
            now = utcnow()
            object.__setattr__(self, "timestamps", Timestamps(created_at=now, updated_at=now))

    def mark_published(self, at: datetime) -> None:
        object.__setattr__(self, "published_at", at)
        _touch(self)


def _dedupe_hashtags(tags: list[Hashtag]) -> list[Hashtag]:
    seen: set[str] = set()
    out: list[Hashtag] = []
    for t in tags:
        v = t.value
        if v in seen:
            continue
        seen.add(v)
        out.append(t)
    return out


def _touch(draft: ContentDraft | PublicationQueueItem) -> None:

    object.__setattr__(draft, "timestamps", draft.timestamps.touch(at=utcnow()))


__all__ = ["ContentDraft", "PublicationQueueItem"]
