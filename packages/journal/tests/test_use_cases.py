"""Testes unitarios dos use cases do journal com repo fake."""

from __future__ import annotations

import pytest
from developer_brain_ai_journal.application.dto import (
    CreateJournalEntryInput,
    UpdateJournalEntryInput,
)
from developer_brain_ai_journal.application.use_cases import (
    CreateJournalEntry,
    DeleteJournalEntry,
    GetJournalEntry,
    ListJournalEntries,
    UpdateJournalEntry,
)
from developer_brain_ai_shared.errors.base import NotFoundError, ValidationError
from developer_brain_ai_shared.kernel.id import TenantId
from journal_fakes import FakeJournalEntryRepository


def _create_input(**overrides) -> CreateJournalEntryInput:
    base = dict(
        title="Estudei FastAPI",
        entry_date="2026-08-06",
        study_minutes=90,
        technologies=["fastapi", "pydantic"],
        tags=["fast-api", "back-end"],
    )
    base.update(overrides)
    return CreateJournalEntryInput(**base)


def test_create_returns_full_dto() -> None:
    import asyncio

    repo = FakeJournalEntryRepository()
    uc = CreateJournalEntry(repo)
    out = asyncio.run(uc.execute(TenantId.new(), _create_input()))
    assert out.id
    assert out.title == "Estudei FastAPI"
    assert out.study_minutes == 90
    assert out.technologies == ["fastapi", "pydantic"]
    assert out.tags == ["fast-api", "back-end"]
    assert out.bugs_found == []
    assert out.resolutions == []
    assert out.notes == ""


def test_create_rejects_divergent_bugs_resolutions() -> None:
    import asyncio

    repo = FakeJournalEntryRepository()
    uc = CreateJournalEntry(repo)
    with pytest.raises(ValidationError):
        asyncio.run(
            uc.execute(
                TenantId.new(),
                _create_input(bugs_found=["b1"], resolutions=[]),
            )
        )


def test_get_returns_entry() -> None:
    import asyncio

    repo = FakeJournalEntryRepository()
    tenant = TenantId.new()
    out = asyncio.run(CreateJournalEntry(repo).execute(tenant, _create_input()))
    fetched = asyncio.run(GetJournalEntry(repo).execute(tenant, out.id))
    assert fetched.id == out.id
    assert fetched.title == "Estudei FastAPI"


def test_get_unknown_raises_not_found() -> None:
    import asyncio

    with pytest.raises(NotFoundError):
        asyncio.run(
            GetJournalEntry(FakeJournalEntryRepository()).execute(
                TenantId.new(),
                "12345678-1234-5678-1234-567812345678",
            )
        )


def test_list_filters_by_tag() -> None:
    import asyncio

    repo = FakeJournalEntryRepository()
    tenant = TenantId.new()
    create = CreateJournalEntry(repo)
    asyncio.run(create.execute(tenant, _create_input(tags=["t-x"])))
    asyncio.run(create.execute(tenant, _create_input(title="Outro", tags=["t-y"])))

    out_x, n_x = asyncio.run(ListJournalEntries(repo).execute(tenant, tag="t-x"))
    assert n_x == 1
    assert out_x[0].tags == ["t-x"]

    out_y, n_y = asyncio.run(ListJournalEntries(repo).execute(tenant, tag="t-y"))
    assert n_y == 1
    assert out_y[0].tags == ["t-y"]


def test_list_filters_by_technology() -> None:
    import asyncio

    repo = FakeJournalEntryRepository()
    tenant = TenantId.new()
    asyncio.run(
        CreateJournalEntry(repo).execute(tenant, _create_input(technologies=["rust", "tokio"]))
    )
    asyncio.run(
        CreateJournalEntry(repo).execute(tenant, _create_input(title="Go", technologies=["go"]))
    )

    out, n = asyncio.run(ListJournalEntries(repo).execute(tenant, technology="rust"))
    assert n == 1
    assert "rust" in out[0].technologies


def test_update_changes_fields_and_touches_timestamp() -> None:
    import asyncio

    repo = FakeJournalEntryRepository()
    tenant = TenantId.new()
    out = asyncio.run(CreateJournalEntry(repo).execute(tenant, _create_input(title="Old")))
    import time

    time.sleep(0.01)
    updated = asyncio.run(
        UpdateJournalEntry(repo).execute(
            tenant,
            out.id,
            UpdateJournalEntryInput(title="New title", study_minutes=30, tags=["x", "y"]),
        )
    )
    assert updated.title == "New title"
    assert updated.study_minutes == 30
    assert updated.tags == ["x", "y"]
    assert updated.updated_at > out.created_at


def test_update_unknown_raises_not_found() -> None:
    import asyncio

    with pytest.raises(NotFoundError):
        asyncio.run(
            UpdateJournalEntry(FakeJournalEntryRepository()).execute(
                TenantId.new(),
                "12345678-1234-5678-1234-567812345678",
                UpdateJournalEntryInput(title="X"),
            )
        )


def test_update_rejects_bugs_found_without_resolutions() -> None:
    import asyncio

    repo = FakeJournalEntryRepository()
    tenant = TenantId.new()
    out = asyncio.run(CreateJournalEntry(repo).execute(tenant, _create_input()))
    with pytest.raises(ValidationError):
        asyncio.run(
            UpdateJournalEntry(repo).execute(
                tenant,
                out.id,
                UpdateJournalEntryInput(bugs_found=["b1"]),
            )
        )


def test_delete_returns_silent_when_existing() -> None:
    import asyncio

    repo = FakeJournalEntryRepository()
    tenant = TenantId.new()
    out = asyncio.run(CreateJournalEntry(repo).execute(tenant, _create_input()))
    asyncio.run(DeleteJournalEntry(repo).execute(tenant, out.id))
    with pytest.raises(NotFoundError):
        asyncio.run(GetJournalEntry(repo).execute(tenant, out.id))


def test_delete_unknown_raises_not_found() -> None:
    import asyncio

    with pytest.raises(NotFoundError):
        asyncio.run(
            DeleteJournalEntry(FakeJournalEntryRepository()).execute(
                TenantId.new(),
                "12345678-1234-5678-1234-567812345678",
            )
        )


def test_isolation_between_tenants() -> None:
    import asyncio

    repo = FakeJournalEntryRepository()
    t1, t2 = TenantId.new(), TenantId.new()
    out1 = asyncio.run(CreateJournalEntry(repo).execute(t1, _create_input()))

    with pytest.raises(NotFoundError):
        asyncio.run(GetJournalEntry(repo).execute(t2, out1.id))


def test_list_pagination_returns_only_first_page() -> None:
    import asyncio

    repo = FakeJournalEntryRepository()
    tenant = TenantId.new()
    create = CreateJournalEntry(repo)
    for i in range(5):
        asyncio.run(create.execute(tenant, _create_input(title=f"D-{i}")))

    out, n = asyncio.run(ListJournalEntries(repo).execute(tenant, page=1, page_size=2))
    assert n == 2
    assert len(out) == 2

    out2, n2 = asyncio.run(ListJournalEntries(repo).execute(tenant, page=2, page_size=2))
    assert n2 == 2
    assert {o.id for o in out}.isdisjoint({o.id for o in out2})
