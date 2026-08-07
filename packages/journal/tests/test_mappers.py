"""Testes unitarios dos mappers ORM <-> JournalEntry (round-trip sem DB)."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

from developer_brain_ai_journal.domain.entry import JournalEntry
from developer_brain_ai_journal.domain.ids import JournalEntryId
from developer_brain_ai_journal.domain.value_objects import EntryDate, StudyMinutes, Tag
from developer_brain_ai_journal.infrastructure.mappers import entry_from_orm, entry_to_orm
from developer_brain_ai_journal.infrastructure.orm import JournalEntryORM
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow


def _make_entry(**overrides) -> JournalEntry:
    now = utcnow()
    base = dict(
        id=JournalEntryId.new(),
        tenant_id=TenantId.new(),
        title="Round trip",
        entry_date=EntryDate(date.today()),
        study_minutes=StudyMinutes(45),
        timestamps=Timestamps(created_at=now, updated_at=now),
        technologies=["rust", "tokio"],
        project="dba",
        difficulties="nada",
        learnings="muito",
        bugs_found=["bug1"],
        resolutions=["res1"],
        next_steps="proximo",
        notes="notas",
        tags=[Tag("rust"), Tag("async")],
    )
    base.update(overrides)
    return JournalEntry.create(**base)


def test_entry_to_orm_serializes_lists_as_json() -> None:
    entry = _make_entry()
    orm = entry_to_orm(entry)
    assert orm.id == entry.id.as_uuid()
    assert orm.tenant_id == entry.tenant_id.as_uuid()
    assert orm.title == "Round trip"
    assert orm.entry_date == entry.entry_date.as_date()
    assert orm.study_minutes == 45
    assert json.loads(orm.technologies) == ["rust", "tokio"]
    assert json.loads(orm.bugs_found) == ["bug1"]
    assert json.loads(orm.resolutions) == ["res1"]
    assert orm.difficulties == "nada"


def test_entry_from_orm_round_trips() -> None:
    entry = _make_entry()
    orm = entry_to_orm(entry)
    rebuilt = entry_from_orm(orm, tag_values=["async", "rust"])
    assert rebuilt.id == entry.id
    assert rebuilt.tenant_id == entry.tenant_id
    assert rebuilt.title == entry.title
    assert rebuilt.study_minutes.as_int() == 45
    assert rebuilt.technologies == ["rust", "tokio"]
    assert rebuilt.bugs_found == ["bug1"]
    assert rebuilt.resolutions == ["res1"]
    assert {str(t) for t in rebuilt.tags} == {"async", "rust"}


def test_entry_from_orm_handles_empty_json() -> None:
    orm = JournalEntryORM(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        title="Empty",
        entry_date=date.today(),
        study_minutes=0,
        technologies="",
        videos="[]",
        links="[]",
        bugs_found="[]",
        resolutions="[]",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    rebuilt = entry_from_orm(orm, tag_values=[])
    assert rebuilt.technologies == []
    assert rebuilt.videos == []
    assert rebuilt.links == []
    assert rebuilt.bugs_found == []
    assert rebuilt.tags == []


def test_entry_from_orm_tolerates_corrupted_json() -> None:
    orm = JournalEntryORM(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        title="Corrupt",
        entry_date=date.today(),
        study_minutes=0,
        technologies="{not-json",
        videos="[]",
        links="[]",
        bugs_found="[]",
        resolutions="[]",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    rebuilt = entry_from_orm(orm, tag_values=[])
    assert rebuilt.technologies == []


def test_entry_to_orm_preserves_timestamps() -> None:
    entry = _make_entry()
    orm = entry_to_orm(entry)
    assert orm.created_at == entry.timestamps.created_at
    assert orm.updated_at == entry.timestamps.updated_at