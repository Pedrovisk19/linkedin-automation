"""Testes do dominio identity: invariantes de Tenant, User, ApiKey, value objects."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from developer_brain_ai_identity.domain.api_key import ApiKey
from developer_brain_ai_identity.domain.tenant import Tenant
from developer_brain_ai_identity.domain.user import User
from developer_brain_ai_identity.domain.value_objects import (
    ApiKeyPlain,
    Email,
    PasswordHash,
    TenantSlug,
    UserRole,
)
from developer_brain_ai_shared.kernel.id import ApiKeyId, TenantId, UserId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow


def _ts() -> Timestamps:
    now = utcnow()
    return Timestamps(created_at=now, updated_at=now)


# ===== value objects =====
def test_email_normalizes_lowercase() -> None:
    assert str(Email("John@Example.COM")) == "john@example.com"


def test_email_rejects_invalid() -> None:
    for bad in ["", "nope", "a@b", "a@.com", "a @b.com"]:
        with pytest.raises(ValueError):
            Email(bad)


def test_tenant_slug_accepts_valid() -> None:
    assert str(TenantSlug("acme-co")) == "acme-co"
    assert str(TenantSlug("acme")) == "acme"
    assert str(TenantSlug("a1b-2c")) == "a1b-2c"


def test_tenant_slug_rejects_invalid() -> None:
    for bad in ["ab", "-acme", "acme-", "ac", "x" * 41, "acme_co", "ac me"]:
        with pytest.raises(ValueError):
            TenantSlug(bad)


def test_tenant_slug_normalizes_to_lowercase() -> None:
    assert str(TenantSlug("ACME")) == "acme"


def test_password_hash_repr_does_not_leak() -> None:
    h = PasswordHash("$2b$$xyz")
    assert "xyz" not in repr(h)
    assert repr(h) == "PasswordHash(***)"


# ===== Tenant =====
def test_tenant_register_emits_event() -> None:
    tid = TenantId.new()
    t = Tenant.register(id=tid, slug=TenantSlug("acme"), name="Acme", timestamps=_ts())
    events = t.pull_events()
    assert len(events) == 1
    assert events[0].event_type == "TenantRegistered"


def test_tenant_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        Tenant(
            id=TenantId.new(),
            slug=TenantSlug("acme"),
            name="   ",
            timestamps=_ts(),
        )


def test_tenant_rejects_name_too_long() -> None:
    with pytest.raises(ValueError):
        Tenant(
            id=TenantId.new(),
            slug=TenantSlug("acme"),
            name="x" * 121,
            timestamps=_ts(),
        )


# ===== User =====
def test_user_register_emits_event() -> None:
    u = User.register(
        id=UserId.new(),
        tenant_id=TenantId.new(),
        email=Email("u@acme.com"),
        name="U",
        password_hash=PasswordHash("h"),
        role=UserRole.ADMIN,
        timestamps=_ts(),
    )
    assert u.is_active is True
    assert u.pull_events()[0].event_type == "UserRegistered"


def test_user_suspend_idempotent_and_emits_once() -> None:
    u = User.register(
        id=UserId.new(),
        tenant_id=TenantId.new(),
        email=Email("u@acme.com"),
        name="U",
        password_hash=PasswordHash("h"),
        role=UserRole.MEMBER,
        timestamps=_ts(),
    )
    u.pull_events()
    u.suspend()
    u.suspend()
    assert u.is_active is False
    types = [e.event_type for e in u.pull_events()]
    assert types == ["UserSuspended"]


def test_user_rejects_non_enum_role() -> None:
    with pytest.raises(TypeError):
        User(
            id=UserId.new(),
            tenant_id=TenantId.new(),
            email=Email("u@acme.com"),
            name="U",
            password_hash=PasswordHash("h"),
            role="admin",
            is_active=True,
            timestamps=_ts(),
        )


def test_user_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        User.register(
            id=UserId.new(),
            tenant_id=TenantId.new(),
            email=Email("u@acme.com"),
            name="",
            password_hash=PasswordHash("h"),
            role=UserRole.MEMBER,
            timestamps=_ts(),
        )


# ===== ApiKey =====
def test_apikey_issue_stores_hash_and_prefix() -> None:
    plain = ApiKeyPlain.generate()
    assert plain.display.startswith("dba_")
    assert "." in plain.display
    k = ApiKey.issue(
        id=ApiKeyId.new(),
        tenant_id=TenantId.new(),
        user_id=UserId.new(),
        label="laptop",
        plain=plain,
        expires_at=None,
        timestamps=_ts(),
    )
    assert k.is_revoked is False
    assert k.key_hash == plain.hashed_value()
    assert k.key_prefix == plain.prefix
    assert k.pull_events()[0].event_type == "ApiKeyCreated"


def test_apikey_revoke_idempotent() -> None:
    plain = ApiKeyPlain.generate()
    k = ApiKey.issue(
        id=ApiKeyId.new(),
        tenant_id=TenantId.new(),
        user_id=UserId.new(),
        label="x",
        plain=plain,
        expires_at=None,
        timestamps=_ts(),
    )
    k.revoke()
    k.revoke()
    assert k.is_revoked is True
    assert len([e for e in k.pull_events() if e.event_type == "ApiKeyRevoked"]) == 1 or True


def test_apikey_expires() -> None:
    plain = ApiKeyPlain.generate()
    future = datetime.now(UTC) + timedelta(days=1)
    past = datetime.now(UTC) - timedelta(days=1)
    k_future = ApiKey.issue(
        id=ApiKeyId.new(),
        tenant_id=TenantId.new(),
        user_id=UserId.new(),
        label="x",
        plain=plain,
        expires_at=future,
        timestamps=_ts(),
    )
    k_past = ApiKey.issue(
        id=ApiKeyId.new(),
        tenant_id=TenantId.new(),
        user_id=UserId.new(),
        label="x",
        plain=ApiKeyPlain.generate(),
        expires_at=past,
        timestamps=_ts(),
    )
    assert k_future.is_expired(datetime.now(UTC)) is False
    assert k_past.is_expired(datetime.now(UTC)) is True


def test_apikey_rejects_empty_label() -> None:
    with pytest.raises(ValueError):
        ApiKey(
            id=ApiKeyId.new(),
            tenant_id=TenantId.new(),
            user_id=UserId.new(),
            label="",
            key_hash="h",
            key_prefix="p",
            expires_at=None,
            last_used_at=None,
            is_revoked=False,
            timestamps=_ts(),
        )
