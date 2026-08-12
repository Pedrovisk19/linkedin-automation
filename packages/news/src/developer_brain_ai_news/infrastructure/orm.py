"""ORM models do news.

Tabela:
- news_items (TenantScoped): 1 item coletado de fonte externa. Dedupe por
  ``content_hash`` (sha256 de url+published_at) unico por tenant.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from developer_brain_ai_shared.persistence.base import Base, TenantScopedMixin, TimestampMixin
from sqlalchemy import DateTime, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column


class NewsItemORM(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "news_items"
    __table_args__ = (
        Index("ix_news_items_tenant_id_id", "tenant_id", "id", unique=True),
        Index("ix_news_items_tenant_hash", "tenant_id", "content_hash", unique=True),
        Index("ix_news_items_tenant_published", "tenant_id", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)


__all__ = ["NewsItemORM"]
