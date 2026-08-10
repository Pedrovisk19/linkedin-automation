"""Testes e2e dos routers do journal via TestClient + DI override (fake repo).

Reaproveita JWTService real; apenas repositories sao fakeados. Mantem context
de tenant entre requests via set_tenant_context (feito pelo Depends current_user).
"""

from __future__ import annotations

from developer_brain_ai_identity.presentation.dependencies import get_current_user_factory
from developer_brain_ai_journal.application.use_cases import (
    CreateJournalEntry,
    DeleteJournalEntry,
    GetJournalEntry,
    ListJournalEntries,
    UpdateJournalEntry,
)
from developer_brain_ai_journal.presentation.routers import build_router
from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.errors.http import mount_domain_error_handlers
from fastapi import FastAPI
from fastapi.testclient import TestClient
from journal_fakes import FakeJournalEntryRepository

SECRET = "test-secret-please-replace-me-12345678901234567890"
ENTRY_PAYLOAD = {
    "title": "Diario do dia",
    "entry_date": "2026-08-06",
    "study_minutes": 90,
    "technologies": ["fastapi", "pydantic"],
    "tags": ["fast-api", "back-end"],
}


def _build_app() -> FastAPI:
    repo = FakeJournalEntryRepository()
    jwt = JWTService(secret=SECRET)
    current_user_dep = get_current_user_factory(jwt)

    router = build_router(
        create_uc=CreateJournalEntry(repo),
        get_uc=GetJournalEntry(repo),
        list_uc=ListJournalEntries(repo),
        update_uc=UpdateJournalEntry(repo),
        delete_uc=DeleteJournalEntry(repo),
        current_user_dep=current_user_dep,
    )
    app = FastAPI()
    mount_domain_error_handlers(app)
    app.include_router(router)
    return app


def _make_token(tenant_id: str, user_id: str) -> str:
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    jwt = JWTService(secret=SECRET)
    pair = jwt.issue_pair(UserId(user_id), TenantId(tenant_id))
    return pair.access_token


def test_journal_protected_requires_bearer() -> None:
    app = _build_app()
    with TestClient(app) as c:
        r = c.get("/journals")
    assert r.status_code == 401
    assert r.json()["detail"] == "bearer token ausente"


def test_create_returns_201_with_full_dto() -> None:
    app = _build_app()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    tid, uid = TenantId.new(), UserId.new()
    token = _make_token(str(tid), str(uid))
    auth = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as c:
        r = c.post("/journals", json=ENTRY_PAYLOAD, headers=auth)
        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "Diario do dia"
        assert body["study_minutes"] == 90
        assert body["technologies"] == ["fastapi", "pydantic"]
        assert body["tags"] == ["fast-api", "back-end"]
        assert body["bugs_found"] == []
        entry_id = body["id"]

        r_get = c.get(f"/journals/{entry_id}", headers=auth)
        assert r_get.status_code == 200
        assert r_get.json()["title"] == "Diario do dia"


def test_create_rejects_with_422_invalid_payload() -> None:
    app = _build_app()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    token = _make_token(str(TenantId.new()), str(UserId.new()))
    bad = {"title": "", "entry_date": "2026-08-06", "study_minutes": 90}
    with TestClient(app) as c:
        r = c.post("/journals", json=bad, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_create_rejects_future_entry_date() -> None:
    app = _build_app()
    from datetime import date, timedelta

    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    token = _make_token(str(TenantId.new()), str(UserId.new()))
    bad = dict(ENTRY_PAYLOAD)
    bad["entry_date"] = (date.today() + timedelta(days=5)).isoformat()
    with TestClient(app) as c:
        r = c.post("/journals", json=bad, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400 or r.status_code == 422


def test_get_unknown_returns_404() -> None:
    app = _build_app()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    token = _make_token(str(TenantId.new()), str(UserId.new()))
    with TestClient(app) as c:
        r = c.get(
            "/journals/12345678-1234-5678-1234-567812345678",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"


def test_list_filters_by_tag() -> None:
    app = _build_app()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    token = _make_token(str(TenantId.new()), str(UserId.new()))
    auth = {"Authorization": f"Bearer {token}"}
    body = dict(ENTRY_PAYLOAD)
    body["tags"] = ["golang"]
    body["title"] = "Estudo Go"
    body2 = dict(ENTRY_PAYLOAD)
    body2["title"] = "Estudo Python"
    with TestClient(app) as c:
        c.post("/journals", json=body, headers=auth)
        c.post("/journals", json=body2, headers=auth)

        r = c.get("/journals?tag=golang", headers=auth)
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 1
        assert items[0]["title"] == "Estudo Go"


def test_list_paginates() -> None:
    app = _build_app()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    token = _make_token(str(TenantId.new()), str(UserId.new()))
    auth = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as c:
        for i in range(5):
            body = dict(ENTRY_PAYLOAD)
            body["title"] = f"D-{i}"
            c.post("/journals", json=body, headers=auth)
        r1 = c.get("/journals?page=1&page_size=2", headers=auth)
        r2 = c.get("/journals?page=2&page_size=2", headers=auth)
        assert len(r1.json()) == 2
        assert len(r2.json()) == 2
        assert {x["id"] for x in r1.json()}.isdisjoint({x["id"] for x in r2.json()})


def test_patch_updates_title() -> None:
    app = _build_app()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    token = _make_token(str(TenantId.new()), str(UserId.new()))
    auth = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as c:
        r = c.post("/journals", json=ENTRY_PAYLOAD, headers=auth)
        eid = r.json()["id"]
        r = c.patch(f"/journals/{eid}", json={"title": "Novo titulo"}, headers=auth)
        assert r.status_code == 200
        assert r.json()["title"] == "Novo titulo"


def test_patch_unknown_returns_404() -> None:
    app = _build_app()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    token = _make_token(str(TenantId.new()), str(UserId.new()))
    with TestClient(app) as c:
        r = c.patch(
            "/journals/12345678-1234-5678-1234-567812345678",
            json={"title": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 404


def test_delete_existing_and_then_404_on_get() -> None:
    app = _build_app()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    token = _make_token(str(TenantId.new()), str(UserId.new()))
    auth = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as c:
        eid = c.post("/journals", json=ENTRY_PAYLOAD, headers=auth).json()["id"]
        r = c.delete(f"/journals/{eid}", headers=auth)
        assert r.status_code == 204
        r = c.get(f"/journals/{eid}", headers=auth)
        assert r.status_code == 404


def test_delete_unknown_returns_404() -> None:
    app = _build_app()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    token = _make_token(str(TenantId.new()), str(UserId.new()))
    with TestClient(app) as c:
        r = c.delete(
            "/journals/12345678-1234-5678-1234-567812345678",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 404


def test_isolation_between_tenants_in_http() -> None:
    app = _build_app()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    t1 = _make_token(str(TenantId.new()), str(UserId.new()))
    t2 = _make_token(str(TenantId.new()), str(UserId.new()))
    with TestClient(app) as c:
        eid = c.post(
            "/journals", json=ENTRY_PAYLOAD, headers={"Authorization": f"Bearer {t1}"}
        ).json()["id"]
        r = c.get(f"/journals/{eid}", headers={"Authorization": f"Bearer {t2}"})
    assert r.status_code == 404
