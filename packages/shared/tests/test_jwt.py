"""Testes do JWTService: issue/decode, tipos, expiracao, segredo curto."""
from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest

from developer_brain_ai_shared.auth import JWTService, TenantId, UserId
from developer_brain_ai_shared.errors import UnauthorizedError

SECRET = "test-secret-please-replace-me-12345678901234567890"


def test_issue_pair_returns_two_distinct_tokens() -> None:
    svc = JWTService(secret=SECRET)
    pair = svc.issue_pair(UserId.new(), TenantId.new())
    assert pair.access_token
    assert pair.refresh_token
    assert pair.access_token != pair.refresh_token


def test_decode_access_succeeds() -> None:
    svc = JWTService(secret=SECRET)
    uid = UserId.new()
    tid = TenantId.new()
    pair = svc.issue_pair(uid, tid)

    payload = svc.decode(pair.access_token, expected_type="access")
    assert payload.user_id == uid
    assert payload.tenant_id == tid
    assert payload.token_type == "access"


def test_decode_refresh_cannot_be_used_as_access() -> None:
    svc = JWTService(secret=SECRET)
    pair = svc.issue_pair(UserId.new(), TenantId.new())
    with pytest.raises(UnauthorizedError):
        svc.decode(pair.refresh_token, expected_type="access")


def test_decode_invalid_token_raises_unauthorized() -> None:
    svc = JWTService(secret=SECRET)
    with pytest.raises(UnauthorizedError):
        svc.decode("not-a-token", expected_type="access")


def test_decode_tampered_token_raises_unauthorized() -> None:
    svc = JWTService(secret=SECRET)
    pair = svc.issue_pair(UserId.new(), TenantId.new())
    tampered = pair.access_token[:-3] + "XXX"
    with pytest.raises(UnauthorizedError):
        svc.decode(tampered, expected_type="access")


def test_expired_token_detected() -> None:
    svc = JWTService(secret=SECRET, access_ttl_seconds=1)
    pair = svc.issue_pair(UserId.new(), TenantId.new())
    time.sleep(2)
    payload = svc.decode(pair.access_token, expected_type="access")
    assert payload.is_expired
    assert datetime.now(UTC) >= payload.expires_at


def test_short_secret_rejected() -> None:
    with pytest.raises(ValueError):
        JWTService(secret="short")