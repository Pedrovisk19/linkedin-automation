"""Composition root parcial do identity: fabricas de use cases para DI."""

from __future__ import annotations

from developer_brain_ai_identity.application.use_cases.create_api_key import CreateApiKey
from developer_brain_ai_identity.application.use_cases.login_user import LoginUser
from developer_brain_ai_identity.application.use_cases.manage_api_keys import (
    ListApiKeys,
    RevokeApiKey,
)
from developer_brain_ai_identity.application.use_cases.refresh_token import RefreshToken
from developer_brain_ai_identity.application.use_cases.register_tenant import RegisterTenant


def build_register_tenant(tenants, users, hasher) -> RegisterTenant:
    return RegisterTenant(tenants, users, hasher)


def build_login_user(tenants, users, hasher, jwt) -> LoginUser:
    return LoginUser(tenants, users, hasher, jwt)


def build_refresh_token(jwt) -> RefreshToken:
    return RefreshToken(jwt)


def build_create_api_key(api_keys) -> CreateApiKey:
    return CreateApiKey(api_keys)


def build_list_api_keys(api_keys) -> ListApiKeys:
    return ListApiKeys(api_keys)


def build_revoke_api_key(api_keys) -> RevokeApiKey:
    return RevokeApiKey(api_keys)


__all__ = [
    "build_create_api_key",
    "build_list_api_keys",
    "build_login_user",
    "build_refresh_token",
    "build_register_tenant",
    "build_revoke_api_key",
]
