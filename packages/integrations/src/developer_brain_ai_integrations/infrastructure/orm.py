"""ORM do integrations: linkedin_tokens (TenantScoped, RLS)."""

from __future__ import annotations

import uuid
from datetime import datetime

from developer_brain_ai_shared.persistence.base import Base, TenantScopedMixin, TimestampMixin
from sqlalchemy import DateTime, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column


class LinkedInTokenORM(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "linkedin_tokens"
    __table_args__ = (Index("ix_linkedin_tokens_tenant_id", "tenant_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    member_urn: Mapped[str] = mapped_column(String(128), nullable=False)
    member_name: Mapped[str] = mapped_column(String(200), nullable=False)


__all__ = ["LinkedInTokenORM"]
