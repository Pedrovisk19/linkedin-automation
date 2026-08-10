"""Mappers ORM <-> Entidades de dominio. Funções puras (nao methods).

Mantém dominio agnostico a SQLAlchemy: a camada infrastructure converte.
"""

from __future__ import annotations

from developer_brain_ai_shared.kernel.id import ApiKeyId, TenantId, UserId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_identity.domain.api_key import ApiKey
from developer_brain_ai_identity.domain.tenant import Tenant
from developer_brain_ai_identity.domain.user import User
from developer_brain_ai_identity.domain.value_objects import (
    Email,
    PasswordHash,
    TenantSlug,
    UserRole,
)
from developer_brain_ai_identity.infrastructure.orm import ApiKeyORM, TenantORM, UserORM


def tenant_to_orm(t: Tenant) -> TenantORM:
    return TenantORM(
        id=t.id.as_uuid(),
        slug=str(t.slug),
        name=t.name,
        created_at=t.timestamps.created_at,
        updated_at=t.timestamps.updated_at,
    )


def tenant_from_orm(o: TenantORM) -> Tenant:
    return Tenant(
        id=TenantId(o.id),
        slug=TenantSlug(o.slug),
        name=o.name,
        timestamps=Timestamps(created_at=o.created_at, updated_at=o.updated_at),
    )


def user_to_orm(u: User) -> UserORM:
    return UserORM(
        id=u.id.as_uuid(),
        tenant_id=u.tenant_id.as_uuid(),
        email=str(u.email),
        name=u.name,
        role=u.role.value,
        password_hash=u.password_hash.value,
        is_active=u.is_active,
        created_at=u.timestamps.created_at,
        updated_at=u.timestamps.updated_at,
    )


def user_from_orm(o: UserORM) -> User:
    return User(
        id=UserId(o.id),
        tenant_id=TenantId(o.tenant_id),
        email=Email(o.email),
        name=o.name,
        role=UserRole(o.role),
        password_hash=PasswordHash(o.password_hash),
        is_active=o.is_active,
        timestamps=Timestamps(created_at=o.created_at, updated_at=o.updated_at),
    )


def api_key_to_orm(k: ApiKey) -> ApiKeyORM:
    return ApiKeyORM(
        id=k.id.as_uuid(),
        tenant_id=k.tenant_id.as_uuid(),
        user_id=k.user_id.as_uuid(),
        label=k.label,
        key_hash=k.key_hash,
        key_prefix=k.key_prefix,
        expires_at=k.expires_at,
        last_used_at=k.last_used_at,
        is_revoked=k.is_revoked,
        created_at=k.timestamps.created_at,
        updated_at=k.timestamps.updated_at,
    )


def api_key_from_orm(o: ApiKeyORM) -> ApiKey:
    return ApiKey(
        id=ApiKeyId(o.id),
        tenant_id=TenantId(o.tenant_id),
        user_id=UserId(o.user_id),
        label=o.label,
        key_hash=o.key_hash,
        key_prefix=o.key_prefix,
        expires_at=o.expires_at,
        last_used_at=o.last_used_at,
        is_revoked=o.is_revoked,
        timestamps=Timestamps(created_at=o.created_at, updated_at=o.updated_at),
    )


__all__ = [
    "api_key_from_orm",
    "api_key_to_orm",
    "tenant_from_orm",
    "tenant_to_orm",
    "user_from_orm",
    "user_to_orm",
]
