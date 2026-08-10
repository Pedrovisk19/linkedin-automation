"""Testes e2e dos routers do content via TestClient + DI override."""

from __future__ import annotations

from content_fakes import (
    FakeContentDraftRepository,
    FakeLinkedInGenerator,
    FakePublicationQueueRepository,
)
from developer_brain_ai_content.application.use_cases import (
    CreateLinkedInDraft,
    EnqueueDraft,
    GenerateLinkedInDraft,
    GetDraft,
    ListDrafts,
    MarkPublished,
    RejectDraft,
)
from developer_brain_ai_content.presentation.routers import build_router
from developer_brain_ai_identity.presentation.dependencies import get_current_user_factory
from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.errors.http import mount_domain_error_handlers
from developer_brain_ai_shared.kernel.id import TenantId, UserId
from fastapi import FastAPI
from fastapi.testclient import TestClient

SECRET = "test-secret-please-replace-me-12345678901234567890"
PAYLOAD = {
    "title": "Migrando para Clean Arch",
    "gancho": "E voce?",
    "texto": "mais um dia, mais um refactor",
    "conclusao": "valeu",
    "pergunta": "qual seu pattern?",
    "cta": "comenta",
    "hashtags": ["#cleanarch", "Python"],
}


def _build_app() -> FastAPI:
    drafts = FakeContentDraftRepository()
    queue = FakePublicationQueueRepository()
    jwt = JWTService(secret=SECRET)
    current_user_dep = get_current_user_factory(jwt)

    app = FastAPI()
    mount_domain_error_handlers(app)
    app.include_router(
        build_router(
            create_linkedin_uc=CreateLinkedInDraft(drafts),
            list_drafts_uc=ListDrafts(drafts),
            get_draft_uc=GetDraft(drafts),
            enqueue_uc=EnqueueDraft(drafts, queue),
            mark_published_uc=MarkPublished(drafts, queue),
            reject_uc=RejectDraft(drafts),
            generate_linkedin_uc=GenerateLinkedInDraft(drafts, FakeLinkedInGenerator()),
            current_user_dep=current_user_dep,
        )
    )
    return app


def _token(tid: str, uid: str) -> str:
    pair = JWTService(secret=SECRET).issue_pair(UserId(uid), TenantId(tid))
    return pair.access_token


def test_protected_requires_bearer() -> None:
    with TestClient(_build_app()) as c:
        r = c.get("/content/drafts")
    assert r.status_code == 401


def test_create_linkedin_returns_201() -> None:
    with TestClient(_build_app()) as c:
        auth = {"Authorization": f"Bearer {_token(str(TenantId.new()), str(UserId.new()))}"}
        r = c.post("/content/linkedin", json=PAYLOAD, headers=auth)
        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "Migrando para Clean Arch"
        assert "#cleanarch" in body["hashtags"]
        assert body["status"] == "pending_review"
        draft_id = body["draft_id"]

        r_get = c.get(f"/content/drafts/{draft_id}", headers=auth)
        assert r_get.status_code == 200
        assert r_get.json()["draft_id"] == draft_id


def test_create_rejects_invalid_hashtag_with_422() -> None:
    bad = dict(PAYLOAD)
    bad["hashtags"] = ["1invalid"]
    with TestClient(_build_app()) as c:
        auth = {"Authorization": f"Bearer {_token(str(TenantId.new()), str(UserId.new()))}"}
        r = c.post("/content/linkedin", json=bad, headers=auth)
    assert r.status_code == 422


def test_list_filters_status() -> None:
    with TestClient(_build_app()) as c:
        tid = TenantId.new()
        auth = {"Authorization": f"Bearer {_token(str(tid), str(UserId.new()))}"}
        for _ in range(3):
            c.post("/content/linkedin", json=PAYLOAD, headers=auth)
        r = c.get("/content/drafts?status=pending_review", headers=auth)
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 3
        assert all(x["content_type"] == "linkedin_post" for x in items)


def test_enqueue_then_publish_flow() -> None:
    with TestClient(_build_app()) as c:
        tid = TenantId.new()
        auth = {"Authorization": f"Bearer {_token(str(tid), str(UserId.new()))}"}
        draft_id = c.post("/content/linkedin", json=PAYLOAD, headers=auth).json()["draft_id"]

        r_enq = c.post(
            f"/content/drafts/{draft_id}/enqueue",
            json="2026-08-10T12:00:00Z",
            headers=auth,
        )
        assert r_enq.status_code == 202

        r_pub = c.post(f"/content/drafts/{draft_id}/publish", headers=auth)
        assert r_pub.status_code == 200
        assert r_pub.json()["status"] == "published"

        r_get = c.get(f"/content/drafts/{draft_id}", headers=auth)
        assert r_get.json()["status"] == "published"


def test_publish_without_enqueue_returns_422() -> None:
    with TestClient(_build_app()) as c:
        tid = TenantId.new()
        auth = {"Authorization": f"Bearer {_token(str(tid), str(UserId.new()))}"}
        draft_id = c.post("/content/linkedin", json=PAYLOAD, headers=auth).json()["draft_id"]
        r = c.post(f"/content/drafts/{draft_id}/publish", headers=auth)
        assert r.status_code == 422


def test_reject_marks_status() -> None:
    with TestClient(_build_app()) as c:
        tid = TenantId.new()
        auth = {"Authorization": f"Bearer {_token(str(tid), str(UserId.new()))}"}
        draft_id = c.post("/content/linkedin", json=PAYLOAD, headers=auth).json()["draft_id"]
        r = c.post(
            f"/content/drafts/{draft_id}/reject",
            json="hook fraco",
            headers=auth,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"


def test_get_unknown_returns_404() -> None:
    with TestClient(_build_app()) as c:
        auth = {"Authorization": f"Bearer {_token(str(TenantId.new()), str(UserId.new()))}"}
        r = c.get(
            "/content/drafts/12345678-1234-5678-1234-567812345678",
            headers=auth,
        )
        assert r.status_code == 404


def test_enqueue_unknown_returns_404() -> None:
    with TestClient(_build_app()) as c:
        auth = {"Authorization": f"Bearer {_token(str(TenantId.new()), str(UserId.new()))}"}
        r = c.post(
            "/content/drafts/12345678-1234-5678-1234-567812345678/enqueue",
            json=None,
            headers=auth,
        )
        assert r.status_code == 404


def test_isolation_between_tenants() -> None:
    with TestClient(_build_app()) as c:
        t1 = _token(str(TenantId.new()), str(UserId.new()))
        t2 = _token(str(TenantId.new()), str(UserId.new()))
        id1 = c.post(
            "/content/linkedin",
            json=PAYLOAD,
            headers={"Authorization": f"Bearer {t1}"},
        ).json()["draft_id"]
        r = c.get(f"/content/drafts/{id1}", headers={"Authorization": f"Bearer {t2}"})
    assert r.status_code == 404


def test_generate_linkedin_returns_201_and_persists() -> None:
    with TestClient(_build_app()) as c:
        tid = TenantId.new()
        auth = {"Authorization": f"Bearer {_token(str(tid), str(UserId.new()))}"}
        r = c.post(
            "/content/linkedin/generate",
            json={"entries": [{"title": "d1"}]},
            headers=auth,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "Post de teste"
        assert body["status"] == "pending_review"
        assert "#fastapi" in body["hashtags"]

        r_get = c.get(f"/content/drafts/{body['draft_id']}", headers=auth)
        assert r_get.status_code == 200
        assert r_get.json()["draft_id"] == body["draft_id"]


def test_generate_linkedin_requires_auth() -> None:
    with TestClient(_build_app()) as c:
        r = c.post("/content/linkedin/generate", json={"entries": []})
    assert r.status_code == 401
