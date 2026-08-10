"""Testes e2e do router /ai/summary via TestClient + DI real + FakeAIProvider + fake journal resolver."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ai_fakes import FakeAgentRunRepository, FakeAIProvider
from developer_brain_ai_ai.application.prompt_engine import PromptEngine
from developer_brain_ai_ai.application.use_cases import SummaryAgent
from developer_brain_ai_ai.presentation.routers import build_router
from developer_brain_ai_identity.presentation.dependencies import get_current_user_factory
from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.errors.http import mount_domain_error_handlers
from developer_brain_ai_shared.kernel.id import TenantId, UserId
from fastapi import FastAPI
from fastapi.testclient import TestClient

SECRET = "test-secret-please-replace-me-12345678901234567890"
PROMPTS = Path(__file__).resolve().parents[3] / "prompts"

ENTRY = {
    "title": "Diario do dia",
    "entry_date": "2026-08-06",
    "study_minutes": 90,
    "technologies": ["fastapi"],
    "learnings": "DI is good",
    "difficulties": "",
    "bugs_found": [],
    "resolutions": [],
}


def _build_app(fake_journal_entries: list[dict]) -> FastAPI:
    jwt = JWTService(secret=SECRET)
    current_user_dep = get_current_user_factory(jwt)

    async def fake_resolver(tenant_id, *, since, until):
        return fake_journal_entries

    provider = FakeAIProvider(
        chat_response=json.dumps(
            {
                "title": "Resumo semanal fake",
                "markdown": "# R\n aprendi fastapi",
                "top_learnings": ["DI is good"],
                "metrics": {"hours": 1},
                "period_kind": "weekly",
            }
        )
    )
    engine = PromptEngine(PROMPTS)
    runs = FakeAgentRunRepository()
    agent = SummaryAgent(provider=provider, prompt_engine=engine, runs=runs)

    app = FastAPI()
    mount_domain_error_handlers(app)
    app.include_router(
        build_router(
            summary_agent=agent,
            journal_list_fn=fake_resolver,
            current_user_dep=current_user_dep,
        )
    )
    return app


def _make_token(tenant_id: str, user_id: str) -> str:
    jwt = JWTService(secret=SECRET)
    pair = jwt.issue_pair(UserId(user_id), TenantId(tenant_id))
    return pair.access_token


def test_summary_protected_requires_bearer() -> None:
    app = _build_app([])
    with TestClient(app) as c:
        r = c.post(
            "/ai/summary",
            json={"period_kind": "weekly", "start_date": "2026-08-01", "end_date": "2026-08-07"},
        )
    assert r.status_code == 401


def test_summary_returns_200_with_output() -> None:
    app = _build_app([ENTRY])
    token = _make_token(str(TenantId.new()), str(UserId.new()))
    with TestClient(app) as c:
        r = c.post(
            "/ai/summary",
            json={"period_kind": "weekly", "start_date": "2026-08-01", "end_date": "2026-08-07"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Resumo semanal fake"
    assert "fastapi" in body["markdown"]
    assert body["top_learnings"] == ["DI is good"]
    assert body["metrics"] == {"hours": 1}


def test_summary_rejects_invalid_period_kind_with_422() -> None:
    app = _build_app([])
    token = _make_token(str(TenantId.new()), str(UserId.new()))
    with TestClient(app) as c:
        r = c.post(
            "/ai/summary",
            json={"period_kind": "yearly", "start_date": "2026-01-01", "end_date": "2026-12-31"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 422


def test_summary_invokes_journal_resolver_with_period_dates() -> None:
    seen_calls: list[dict] = []
    jwt = JWTService(secret=SECRET)
    current_user_dep = get_current_user_factory(jwt)
    app = FastAPI()
    mount_domain_error_handlers(app)

    async def fake_resolver(tenant_id, *, since, until):
        seen_calls.append({"since": since, "until": until, "tenant_id": str(tenant_id)})
        return [ENTRY]

    from developer_brain_ai_ai.presentation.routers import build_router

    agent = SummaryAgent(
        provider=FakeAIProvider(chat_response='{"title":"x","top_learnings":[],"metrics":{}}'),
        prompt_engine=PromptEngine(PROMPTS),
        runs=FakeAgentRunRepository(),
    )
    app.include_router(
        build_router(
            summary_agent=agent,
            journal_list_fn=fake_resolver,
            current_user_dep=current_user_dep,
        )
    )
    token = _make_token(str(TenantId.new()), str(UserId.new()))
    with TestClient(app) as c:
        r = c.post(
            "/ai/summary",
            json={"period_kind": "monthly", "start_date": "2026-01-01", "end_date": "2026-01-31"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    assert len(seen_calls) == 1
    assert seen_calls[0]["since"] == date(2026, 1, 1)
    assert seen_calls[0]["until"] == date(2026, 1, 31)


def test_summary_persists_run_behind_the_scenes() -> None:
    jwt = JWTService(secret=SECRET)
    current_user_dep = get_current_user_factory(jwt)
    runs = FakeAgentRunRepository()

    async def fake_resolver(tenant_id, *, since, until):
        return [ENTRY]

    from developer_brain_ai_ai.presentation.routers import build_router

    agent = SummaryAgent(
        provider=FakeAIProvider(chat_response='{"title":"ok"}'),
        prompt_engine=PromptEngine(PROMPTS),
        runs=runs,
    )
    app = FastAPI()
    mount_domain_error_handlers(app)
    app.include_router(
        build_router(
            summary_agent=agent,
            journal_list_fn=fake_resolver,
            current_user_dep=current_user_dep,
        )
    )
    token = _make_token(str(TenantId.new()), str(UserId.new()))
    with TestClient(app) as c:
        c.post(
            "/ai/summary",
            json={"period_kind": "daily", "start_date": "2026-08-06", "end_date": "2026-08-06"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert len(runs.saved) == 1
    assert runs.saved[0].agent.value == "summary"
