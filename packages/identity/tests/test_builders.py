"""Testes dos builders de use_cases (DI factories) do identity."""
from __future__ import annotations

from developer_brain_ai_identity.application.use_cases import (
    build_create_api_key,
    build_list_api_keys,
    build_login_user,
    build_refresh_token,
    build_register_tenant,
    build_revoke_api_key,
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

from identity_fakes import (
    FakeApiKeyRepository,
    FakePasswordHasher,
    FakeTenantRepository,
    FakeUserRepository,
)

SECRET = "test-secret-please-replace-me-12345678901234567890"


def test_build_register_tenant_returns_use_case() -> None:
    uc = build_register_tenant(
        FakeTenantRepository(), FakeUserRepository(), FakePasswordHasher()
    )
    assert isinstance(uc, RegisterTenant)


def test_build_login_user_returns_use_case() -> None:
    tenants, users, hasher = FakeTenantRepository(), FakeUserRepository(), FakePasswordHasher()
    jwt = JWTService(secret=SECRET)
    uc = build_login_user(tenants, users, hasher, jwt)
    assert isinstance(uc, LoginUser)


def test_build_refresh_token_returns_use_case() -> None:
    jwt = JWTService(secret=SECRET)
    assert isinstance(build_refresh_token(jwt), RefreshToken)


def test_build_create_api_key_returns_use_case() -> None:
    assert isinstance(build_create_api_key(FakeApiKeyRepository()), CreateApiKey)


def test_build_list_api_keys_returns_use_case() -> None:
    assert isinstance(build_list_api_keys(FakeApiKeyRepository()), ListApiKeys)


def test_build_revoke_api_key_returns_use_case() -> None:
    assert isinstance(build_revoke_api_key(FakeApiKeyRepository()), RevokeApiKey)