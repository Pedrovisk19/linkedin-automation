"""Composition helper que monta todos use cases + router do identity em DI."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker
from fastapi import APIRouter

from developer_brain_ai_identity.application.use_cases import (
    build_create_api_key,
    build_list_api_keys,
    build_login_user,
    build_refresh_token,
    build_register_tenant,
    build_revoke_api_key,
)
from developer_brain_ai_identity.infrastructure.adapters import BcryptPasswordHasher
from developer_brain_ai_identity.infrastructure.repositories import (
    SqlAlchemyApiKeyRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUserRepository,
)
from developer_brain_ai_identity.presentation.dependencies import get_current_user_factory
from developer_brain_ai_identity.presentation.routers import build_router
from developer_brain_ai_shared.auth.jwt import JWTService


def mount_identity(
    *,
    session_factory: async_sessionmaker,
    jwt: JWTService,
) -> APIRouter:
    """Recebe session_factory + jwt do composition root; devolve router pronto p/ include."""
    tenants = SqlAlchemyTenantRepository(session_factory)
    users = SqlAlchemyUserRepository(session_factory)
    api_keys = SqlAlchemyApiKeyRepository(session_factory)
    hasher = BcryptPasswordHasher()

    register_uc = build_register_tenant(tenants, users, hasher)
    login_uc = build_login_user(tenants, users, hasher, jwt)
    refresh_uc = build_refresh_token(jwt)
    create_api_key_uc = build_create_api_key(api_keys)
    list_api_keys_uc = build_list_api_keys(api_keys)
    revoke_api_key_uc = build_revoke_api_key(api_keys)

    current_user_dep = get_current_user_factory(jwt)

    return build_router(
        register_uc=register_uc,
        login_uc=login_uc,
        refresh_uc=refresh_uc,
        create_api_key_uc=create_api_key_uc,
        list_api_keys_uc=list_api_keys_uc,
        revoke_api_key_uc=revoke_api_key_uc,
        current_user_dep=current_user_dep,
    )


__all__ = ["mount_identity"]