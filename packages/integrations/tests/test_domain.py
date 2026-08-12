"""Testes do agregado LinkedInToken (regras de dominio)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from developer_brain_ai_integrations.domain.aggregates import LinkedInToken
from developer_brain_ai_shared.errors.base import ValidationError
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import utcnow


def _base_kwargs(**overrides):
    now = utcnow()
    kwargs = {
        "id": object(),
        "tenant_id": TenantId.new(),
        "access_token": "access",
        "refresh_token": "refresh",
        "access_expires_at": now + timedelta(hours=1),
        "refresh_expires_at": now + timedelta(days=30),
        "member_urn": "urn:li:person:1",
        "member_name": "Fulano",
    }
    kwargs.update(overrides)
    return kwargs


def test_creates_token_with_timestamps() -> None:
    t = LinkedInToken(**_base_kwargs())
    assert t.timestamps.created_at.tzinfo is not None
    assert t.access_is_expired is False


def test_rejects_blank_access_token() -> None:
    with pytest.raises(ValueError):
        LinkedInToken(**_base_kwargs(access_token="   "))


def test_rejects_blank_refresh_token() -> None:
    with pytest.raises(ValueError):
        LinkedInToken(**_base_kwargs(refresh_token=""))


def test_rejects_naive_expiration() -> None:
    now = datetime.now()  # naive
    with pytest.raises(ValueError):
        LinkedInToken(**_base_kwargs(access_expires_at=now))


def test_rejects_expired_refresh() -> None:
    now = utcnow()
    with pytest.raises(ValidationError):
        LinkedInToken(**_base_kwargs(refresh_expires_at=now - timedelta(minutes=1)))


def test_rejects_blank_member_urn() -> None:
    with pytest.raises(ValueError):
        LinkedInToken(**_base_kwargs(member_urn=""))


def test_access_expired_when_past_with_skew() -> None:
    now = utcnow()
    t = LinkedInToken(**_base_kwargs(access_expires_at=now + timedelta(seconds=10)))
    assert t.access_is_expired is True  # skew de 60s


def test_with_refreshed_replaces_tokens_and_touches() -> None:
    t = LinkedInToken(**_base_kwargs())
    updated_at = t.timestamps.updated_at
    novo = t.with_refreshed(
        access_token="new-access",
        refresh_token="new-refresh",
        access_expires_at=utcnow() + timedelta(hours=1),
        refresh_expires_at=utcnow() + timedelta(days=30),
    )
    assert novo.access_token == "new-access"
    assert novo.refresh_token == "new-refresh"
    assert novo.member_urn == t.member_urn
    assert novo.timestamps.updated_at >= updated_at
    assert t.access_token == "access"  # imutavel
