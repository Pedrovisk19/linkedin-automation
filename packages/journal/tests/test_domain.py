"""Testes do dominio do journal: value objects + invariantes do JournalEntry."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from developer_brain_ai_journal.domain.entry import JournalEntry
from developer_brain_ai_journal.domain.ids import JournalEntryId
from developer_brain_ai_journal.domain.value_objects import EntryDate, StudyMinutes, Tag
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow


def _ts() -> Timestamps:
    now = utcnow()
    return Timestamps(created_at=now, updated_at=now)


# === value objects ===
def test_tag_lowercases_and_normalizes() -> None:
    assert str(Tag("  FastAPI  ")) == "fastapi"
    assert str(Tag("py-3_14")) == "py-3_14"


def test_tag_rejects_invalid() -> None:
    for bad in ["", "x" * 41, "Fast API", "-dashed-start", "_underscore-start"]:
        with pytest.raises(ValueError):
            Tag(bad)


def test_study_minutes_bounds() -> None:
    assert StudyMinutes(0).as_int() == 0
    assert StudyMinutes(60).as_int() == 60
    with pytest.raises(ValueError):
        StudyMinutes(-1)
    with pytest.raises(ValueError):
        StudyMinutes(1441)


def test_entry_date_rejects_future() -> None:
    with pytest.raises(ValueError):
        EntryDate(date.today() + timedelta(days=1))


def test_entry_date_accepts_today_and_past() -> None:
    EntryDate(date.today())
    EntryDate(date.today() - timedelta(days=30))


# === JournalEntry ===
def _build_entry(**overrides) -> JournalEntry:
    base = dict(
        id=JournalEntryId.new(),
        tenant_id=TenantId.new(),
        title="Diario do dia",
        entry_date=EntryDate(date.today()),
        study_minutes=StudyMinutes(120),
        timestamps=_ts(),
    )
    base.update(overrides)
    return JournalEntry.create(**base)


def test_create_emits_event() -> None:
    e = _build_entry()
    types = [e.event_type for e in e.pull_events()]
    assert types == ["JournalEntryCreated"]


def test_rejects_empty_title() -> None:
    with pytest.raises(ValueError):
        _build_entry(title="   ")


def test_rejects_title_too_long() -> None:
    with pytest.raises(ValueError):
        _build_entry(title="x" * 201)


def test_rejects_bugs_fixed_lengths_diverge() -> None:
    with pytest.raises(ValueError):
        _build_entry(bugs_found=["x"], resolutions=[])


def test_accepts_zero_bugs() -> None:
    e = _build_entry()
    assert e.bugs_found == []


def test_rejects_empty_tech_in_list() -> None:
    with pytest.raises(ValueError):
        _build_entry(technologies=["Go", "  "])


def test_rejects_empty_video_in_list() -> None:
    with pytest.raises(ValueError):
        _build_entry(videos=["https://x", ""])


def test_rejects_empty_link_in_list() -> None:
    with pytest.raises(ValueError):
        _build_entry(links=["https://a.com", ""])


def test_update_emits_updated_event_and_touches_timestamp() -> None:
    e = _build_entry(title="Old")
    import time

    time.sleep(0.01)
    e.update(title="New", technologies=["fastapi"])
    assert e.title == "New"
    assert e.technologies == ["fastapi"]
    assert e.timestamps.updated_at > e.timestamps.created_at
    events = e.pull_events()
    assert events[-1].event_type == "JournalEntryUpdated"


def test_update_rejects_bugs_found_without_resolutions() -> None:
    e = _build_entry()
    with pytest.raises(ValueError):
        e.update(bugs_found=["b1"])


def test_update_rejects_resolutions_without_bugs_found() -> None:
    e = _build_entry()
    with pytest.raises(ValueError):
        e.update(resolutions=["r1"])


def test_update_accepts_paired_bugs_resolutions() -> None:
    e = _build_entry()
    e.update(bugs_found=["b1"], resolutions=["r1"])
    assert e.bugs_found == ["b1"]
    assert e.resolutions == ["r1"]


def test_update_rejects_invalid_title() -> None:
    e = _build_entry()
    with pytest.raises(ValueError):
        e.update(title="")
    with pytest.raises(ValueError):
        e.update(title="x" * 201)


def test_mark_deleted_emits_event() -> None:
    e = _build_entry()
    e.mark_deleted()
    events = e.pull_events()
    assert events[-1].event_type == "JournalEntryDeleted"


def test_default_tags_empty() -> None:
    e = _build_entry()
    assert e.tags == []
    assert e.technologies == []
    assert e.videos == []
    assert e.links == []


def test_update_tags_via_list_of_str() -> None:
    e = _build_entry()
    e.update(tags=["fast-api", "pytest", "FAST-API"])  # duplicate após normalizar
    assert {str(t) for t in e.tags} == {"fast-api", "pytest"}
