"""ORM do discord: discord_requests (TenantScoped, RLS)."""

from __future__ import annotations

import uuid
from datetime import datetime

from developer_brain_ai_shared.persistence.base import (
    Base,
    TenantScopedMixin,
    TimestampMixin,
    tenant_scoped_index,
)
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column


class DiscordRequestORM(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "discord_requests"
    __table_args__ = (*tenant_scoped_index("discord_requests"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


__all__ = ["DiscordRequestORM"]
