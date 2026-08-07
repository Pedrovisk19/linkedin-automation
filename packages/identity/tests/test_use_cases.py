"""Testes dos use cases do identity com repos fakes (sem IO)."""
from __future__ import annotations

import asyncio

import pytest

from developer_brain_ai_identity.application.dto import (
    CreateApiKeyInput,
    LoginInput,
    RefreshInput,
    RegisterTenantInput,
)
from developer_brain_ai_identity.application.use_cases.create_api_key import CreateApiKey
from developer_brain_ai_identity.application.use_cases.login_user import LoginUser
from developer_brain_ai_identity.application.use_cases.manage_api_keys import (
    ListApiKeys,
    RevokeApiKey,
)
from developer_brain_ai_identity.application.use_cases.refresh_token import RefreshToken
from developer_brain_ai_identity.application.use_cases.register_tenant import RegisterTenant
from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.errors.base import ConflictError, NotFoundError, UnauthorizedError

from fakes import (
    FakeApiKeyRepository,
    FakePasswordHasher,
    FakeTenantRepository,
    FakeUserRepository,
)

SECRET = "test-secret-please-replace-me-12345678901234567890"


def _register_uc(tenants=None, users=None, hasher=None):
    return RegisterTenant(
        tenants or FakeTenantRepository(),
        users or FakeUserRepository(),
        hasher or FakePasswordHasher(),
    )


def _login_uc(tenants, users, hasher=None, jwt=None):
    return LoginUser(
        tenants,
        users,
        hasher or FakePasswordHasher(),
        jwt or JWTService(secret=SECRET),
    )


def test_register_tenant_creates_tenant_and_admin_user() -> None:
    tenants, users, hasher = FakeTenantRepository(), FakeUserRepository(), FakePasswordHasher()
    out = asyncio.run(
        _register_uc(tenants, users, hasher).execute(
            RegisterTenantInput(
                tenant_slug="acme",
                tenant_name="Acme",
                admin_email="admin@acme.com",
                admin_name="Admin",
                admin_password="verystrong-123!",
            )
        )
    )
    assert out.email == "admin@acme.com"
    assert out.tenant_id and out.user_id
    assert asyncio.run(tenants.slug_exists(__import__("developer_brain_ai_identity.domain.value_objects", fromlist=["TenantSlug"]).TenantSlug("acme"))) is True


def test_register_tenant_rejects_dup_slug() -> None:
    tenants, users, hasher = FakeTenantRepository(), FakeUserRepository(), FakePasswordHasher()
    payload = RegisterTenantInput(
        tenant_slug="dupe",
        tenant_name="A",
        admin_email="a@a.com",
        admin_name="A",
        admin_password="verystrong-123!",
    )
    asyncio.run(_register_uc(tenants, users, hasher).execute(payload))
    with pytest.raises(ConflictError):
        asyncio.run(_register_uc(tenants, users, hasher).execute(payload))


def test_register_tenant_rejects_dup_email() -> None:
    uc = _register_uc()
    asyncio.run(
        uc.execute(
            RegisterTenantInput(
                tenant_slug="aaa",
                tenant_name="A",
                admin_email="dup@a.com",
                admin_name="A",
                admin_password="verystrong-123!",
            )
        )
    )
    uc2 = _register_uc(
        tenants=uc._tenants,
        users=uc._users,
        hasher=uc._hasher,
    )
    with pytest.raises(ConflictError):
        asyncio.run(
            uc2.execute(
                RegisterTenantInput(
                    tenant_slug="dupe",
                    tenant_name="B",
                    admin_email="dup@a.com",
                    admin_name="B",
                    admin_password="verystrong-123!",
                )
            )
        )


def test_register_tenant_rejects_weak_password() -> None:
    uc = _register_uc()
    with pytest.raises(Exception):
        asyncio.run(
            uc.execute(
                RegisterTenantInput(
                    tenant_slug="t3",
                    tenant_name="A",
                    admin_email="a@a.com",
                    admin_name="A",
                    admin_password="short",
                )
            )
        )


def test_login_success_returns_token_pair() -> None:
    tenants, users, hasher = FakeTenantRepository(), FakeUserRepository(), FakePasswordHasher()
    asyncio.run(
        _register_uc(tenants, users, hasher).execute(
            RegisterTenantInput(
                tenant_slug="acme",
                tenant_name="Acme",
                admin_email="admin@acme.com",
                admin_name="Admin",
                admin_password="verystrong-123!",
            )
        )
    )

    out = asyncio.run(
        _login_uc(tenants, users, hasher).execute(
            LoginInput(tenant_slug="acme", email="admin@acme.com", password="verystrong-123!")
        )
    )
    assert out.access_token
    assert out.refresh_token
    assert out.token_type == "Bearer"


def test_login_unknown_tenant_unified_error() -> None:
    uc = _login_uc(FakeTenantRepository(), FakeUserRepository())
    with pytest.raises(UnauthorizedError):
        asyncio.run(
            uc.execute(
                LoginInput(tenant_slug="ghost", email="a@b.com", password="x" * 12)
            )
        )


def test_login_unknown_user_unified_error() -> None:
    tenants, users, hasher = FakeTenantRepository(), FakeUserRepository(), FakePasswordHasher()
    asyncio.run(
        _register_uc(tenants, users, hasher).execute(
            RegisterTenantInput(
                tenant_slug="acme",
                tenant_name="A",
                admin_email="admin@acme.com",
                admin_name="A",
                admin_password="verystrong-123!",
            )
        )
    )
    uc = _login_uc(tenants, users, hasher)
    with pytest.raises(UnauthorizedError):
        asyncio.run(
            uc.execute(
                LoginInput(tenant_slug="acme", email="ghost@acme.com", password="verystrong-123!")
            )
        )


def test_login_wrong_password_unified_error() -> None:
    tenants, users, hasher = FakeTenantRepository(), FakeUserRepository(), FakePasswordHasher()
    asyncio.run(
        _register_uc(tenants, users, hasher).execute(
            RegisterTenantInput(
                tenant_slug="acme",
                tenant_name="A",
                admin_email="admin@acme.com",
                admin_name="A",
                admin_password="verystrong-123!",
            )
        )
    )
    uc = _login_uc(tenants, users, hasher)
    with pytest.raises(UnauthorizedError):
        asyncio.run(
            uc.execute(
                LoginInput(tenant_slug="acme", email="admin@acme.com", password="WROOONG-123!")
            )
        )


def test_login_suspended_user_unified_error() -> None:
    tenants, users, hasher = FakeTenantRepository(), FakeUserRepository(), FakePasswordHasher()
    asyncio.run(
        _register_uc(tenants, users, hasher).execute(
            RegisterTenantInput(
                tenant_slug="acme",
                tenant_name="A",
                admin_email="admin@acme.com",
                admin_name="A",
                admin_password="verystrong-123!",
            )
        )
    )
    u = asyncio.run(users.get_by_email(__import__("developer_brain_ai_identity.domain.value_objects", fromlist=["Email"]).Email("admin@acme.com")))
    u.suspend()
    asyncio.run(users.save(u))

    uc = _login_uc(tenants, users, hasher)
    with pytest.raises(UnauthorizedError):
        asyncio.run(
            uc.execute(
                LoginInput(tenant_slug="acme", email="admin@acme.com", password="verystrong-123!")
            )
        )


def test_refresh_returns_new_pair() -> None:
    jwt = JWTService(secret=SECRET)
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    pair = jwt.issue_pair(UserId.new(), TenantId.new())
    out = asyncio.run(RefreshToken(jwt).execute(RefreshInput(refresh_token=pair.refresh_token)))
    assert out.access_token != pair.access_token
    assert out.refresh_token != pair.refresh_token


def test_refresh_rejects_access_token() -> None:
    jwt = JWTService(secret=SECRET)
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    pair = jwt.issue_pair(UserId.new(), TenantId.new())
    with pytest.raises(UnauthorizedError):
        asyncio.run(RefreshToken(jwt).execute(RefreshInput(refresh_token=pair.access_token)))


def test_refresh_rejects_garbage() -> None:
    jwt = JWTService(secret=SECRET)
    with pytest.raises(UnauthorizedError):
        asyncio.run(RefreshToken(jwt).execute(RefreshInput(refresh_token="not-a-token")))


def test_create_api_key_returns_display_once() -> None:
    repo = FakeApiKeyRepository()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    tid, uid = TenantId.new(), UserId.new()
    out = asyncio.run(
        CreateApiKey(repo).execute(tid, uid, CreateApiKeyInput(label="laptop"))
    )
    assert out.key_display.startswith("dba_")
    assert "." in out.key_display
    assert out.label == "laptop"
    assert out.prefix
    saved = asyncio.run(repo.get_by_prefix(tid, out.prefix))
    assert saved is not None
    assert saved.key_hash != out.key_display


def test_list_api_keys_returns_user_keys() -> None:
    repo = FakeApiKeyRepository()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    tid, uid = TenantId.new(), UserId.new()
    asyncio.run(CreateApiKey(repo).execute(tid, uid, CreateApiKeyInput(label="k1")))
    asyncio.run(CreateApiKey(repo).execute(tid, uid, CreateApiKeyInput(label="k2")))
    items = asyncio.run(ListApiKeys(repo).execute(uid))
    assert len(items) == 2
    assert {i.label for i in items} == {"k1", "k2"}


def test_revoke_api_key_marks_revoked() -> None:
    repo = FakeApiKeyRepository()
    from developer_brain_ai_shared.kernel.id import TenantId, UserId

    tid, uid = TenantId.new(), UserId.new()
    out = asyncio.run(CreateApiKey(repo).execute(tid, uid, CreateApiKeyInput(label="x")))
    asyncio.run(RevokeApiKey(repo).execute(out.api_key_id))
    key = asyncio.run(repo.get_by_id(__import__("developer_brain_ai_shared.kernel.id", fromlist=["ApiKeyId"]).ApiKeyId(out.api_key_id)))
    assert key is not None and key.is_revoked is True


def test_revoke_unknown_raises_not_found() -> None:
    repo = FakeApiKeyRepository()
    with pytest.raises(NotFoundError):
        asyncio.run(RevokeApiKey(repo).execute("12345678-1234-5678-1234-567812345678"))