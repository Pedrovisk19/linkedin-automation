"""Declarative base compartilhada + mixins DeclarativeBase central.

Toda ORM herda de ``Base``. ``TenantScopedMixin`` adiciona ``tenant_id`` e
``__table_args__`` com indice composto ``(tenant_id, id)`` — alinhado ao RLS.

Importante: este modulo pode importar SQLAlchemy (camada de infra), porem NUNCA
e importado por ``domain``. A separacao entre ``domain`` (puro) e ``infra ORM``
e garantida por testes de arquitetura (Fase 1).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Raiz de toda ORM. Metadata centralizada (usada pelo Alembic)."""


class TenantScopedMixin:
    """Mixin que adiciona ``tenant_id`` com FK para a tabela ``tenants``."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


class TimestampMixin:
    """created_at/updated_at com default server-side."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def tenant_scoped_index(table_name: str) -> list[Index]:
    """Indice otimizado para RLS: (tenant_id, id). Retorna lista p/ __table_args__."""
    return [Index(f"ix_{table_name}_tenant_id_id", "tenant_id", "id")]


__all__ = ["Base", "TenantScopedMixin", "TimestampMixin", "tenant_scoped_index"]
