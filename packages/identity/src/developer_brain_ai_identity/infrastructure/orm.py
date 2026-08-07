"""ORM models do identity.

- TenantORM: SEM tenant_id (e a propria raiz do tenant). Visivel p/ lookup por slug.
- UserORM, ApiKeyORM: usam TenantScopedMixin (RLS por tenant_id).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from developer_brain_ai_shared.persistence.base import (
    Base,
    TenantScopedMixin,
    TimestampMixin,
)


class TenantORM(TimestampMixin, Base):
    __tablename__ = "tenants"
    __table_args__ = (Index("ix_tenants_slug", "slug", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class UserORM(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_tenant_id_id", "tenant_id", "id", unique=True),
        Index("ix_users_tenant_email", "tenant_id", "email", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ApiKeyORM(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_tenant_id_id", "tenant_id", "id", unique=True),
        Index("ix_api_keys_tenant_prefix", "tenant_id", "key_prefix"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(24), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


__all__ = ["TenantORM", "UserORM", "ApiKeyORM"]