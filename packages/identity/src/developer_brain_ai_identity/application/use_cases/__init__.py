"""Composition root parcial do identity: fabricas de use cases para DI."""

from __future__ import annotations

from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.auth.password import PasswordHasher

from developer_brain_ai_identity.application.use_cases.create_api_key import CreateApiKey
from developer_brain_ai_identity.application.use_cases.login_user import LoginUser
from developer_brain_ai_identity.application.use_cases.manage_api_keys import (
    ListApiKeys,
    RevokeApiKey,
)
from developer_brain_ai_identity.application.use_cases.refresh_token import RefreshToken
from developer_brain_ai_identity.application.use_cases.register_tenant import RegisterTenant
from developer_brain_ai_identity.domain.api_key_repository import ApiKeyRepository
from developer_brain_ai_identity.domain.repositories import TenantRepository, UserRepository


def build_register_tenant(
    tenants: TenantRepository, users: UserRepository, hasher: PasswordHasher
) -> RegisterTenant:
    return RegisterTenant(tenants, users, hasher)


def build_login_user(
    tenants: TenantRepository,
    users: UserRepository,
    hasher: PasswordHasher,
    jwt: JWTService,
) -> LoginUser:
    return LoginUser(tenants, users, hasher, jwt)


def build_refresh_token(jwt: JWTService) -> RefreshToken:
    return RefreshToken(jwt)


def build_create_api_key(api_keys: ApiKeyRepository) -> CreateApiKey:
    return CreateApiKey(api_keys)


def build_list_api_keys(api_keys: ApiKeyRepository) -> ListApiKeys:
    return ListApiKeys(api_keys)


def build_revoke_api_key(api_keys: ApiKeyRepository) -> RevokeApiKey:
    return RevokeApiKey(api_keys)


__all__ = [
    "build_create_api_key",
    "build_list_api_keys",
    "build_login_user",
    "build_refresh_token",
    "build_register_tenant",
    "build_revoke_api_key",
]
