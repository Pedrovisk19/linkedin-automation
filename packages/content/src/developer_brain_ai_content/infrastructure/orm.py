"""ORM models do content.

Tabelas:
- content_drafts (TenantScoped): drafts gerados por agentes. metadata em JSON
  (gancho, conclusao, pergunta, cta, source_entry_ids). hashtags em JSON.
- publication_queue_items (TenantScoped): intent de publicar um draft agendado.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from developer_brain_ai_shared.persistence.base import Base, TenantScopedMixin, TimestampMixin
from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column


class ContentDraftORM(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "content_drafts"
    __table_args__ = (
        Index("ix_content_drafts_tenant_id_id", "tenant_id", "id", unique=True),
        Index("ix_content_drafts_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review")


class PublicationQueueItemORM(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "publication_queue_items"
    __table_args__ = (
        Index("ix_publication_queue_tenant_id_id", "tenant_id", "id", unique=True),
        Index("ix_publication_queue_tenant_scheduled", "tenant_id", "scheduled_for"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("content_drafts.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


__all__ = ["ContentDraftORM", "PublicationQueueItemORM"]
