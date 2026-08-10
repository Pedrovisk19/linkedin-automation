"""Smoke test: FastAPI sobe e /healthz responde. Garante que o composition root eh importavel."""

from __future__ import annotations

import sys
from pathlib import Path

apps_api = Path(__file__).resolve().parents[1] / "apps" / "api"
if str(apps_api) not in sys.path:
    sys.path.insert(0, str(apps_api))

from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def test_healthz_ok() -> None:
    with TestClient(app) as client:
        resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
