"""ORM models do journal.

Tabelas:
- journal_entries (TenantScoped)
- journal_entry_tags (join, unique por (entry_id, tag_id))
- tags (lookup por tenant, unique por (tenant_id, value)).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from developer_brain_ai_shared.persistence.base import Base, TenantScopedMixin, TimestampMixin


class JournalEntryORM(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        Index("ix_journal_entries_tenant_id_id", "tenant_id", "id", unique=True),
        Index("ix_journal_entries_tenant_date", "tenant_id", "entry_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    study_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    technologies: Mapped[list[str]] = mapped_column(Text, nullable=False, default="[]")
    project: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    book: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    course: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    videos: Mapped[list[str]] = mapped_column(Text, nullable=False, default="[]")
    links: Mapped[list[str]] = mapped_column(Text, nullable=False, default="[]")
    difficulties: Mapped[str] = mapped_column(Text, nullable=False, default="")
    learnings: Mapped[str] = mapped_column(Text, nullable=False, default="")
    bugs_found: Mapped[list[str]] = mapped_column(Text, nullable=False, default="[]")
    resolutions: Mapped[list[str]] = mapped_column(Text, nullable=False, default="[]")
    next_steps: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class TagORM(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (
        Index("ix_tags_tenant_value", "tenant_id", "value", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    value: Mapped[str] = mapped_column(String(40), nullable=False)


class JournalEntryTagORM(Base):
    __tablename__ = "journal_entry_tags"
    __table_args__ = (
        Index("ix_jet_entry_tag", "journal_entry_id", "tag_id", unique=True),
    )

    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )


__all__ = ["JournalEntryORM", "TagORM", "JournalEntryTagORM"]