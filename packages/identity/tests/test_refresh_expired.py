"""Cobre o ramo is_expired do RefreshToken montando JWT expirado manualmente."""
from __future__ import annotations

import asyncio
import time

import pytest
from jose import jwt as _jwt

from developer_brain_ai_identity.application.use_cases.refresh_token import RefreshToken
from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.errors import UnauthorizedError
from developer_brain_ai_shared.kernel.id import TenantId, UserId

SECRET = "test-secret-please-replace-me-12345678901234567890"


def test_refresh_expired_token_raises_unauthorized() -> None:
    svc = JWTService(secret=SECRET, refresh_ttl_seconds=1)
    pair = svc.issue_pair(UserId.new(), TenantId.new())
    time.sleep(2)
    with pytest.raises(UnauthorizedError):
        asyncio.run(RefreshToken(svc).execute(__import__("developer_brain_ai_identity.application.dto", fromlist=["RefreshInput"]).RefreshInput(refresh_token=pair.refresh_token)))