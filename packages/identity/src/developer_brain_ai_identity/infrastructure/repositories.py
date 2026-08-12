"""Repositorios SQLAlchemy do identity.

Cada repo injeta ``async_sessionmaker``. Queries em users/api_keys rodam sob
RLS (SET LOCAL emitido pelo UnitOfWork no composition root ou por helper local
para read-only sem UoW explicito).

IMPORTANTE: a camada application recebe pela DI uma Factory destes repos; aqui
NAO fazemos set_tenant_context (responsabilidade do caller / middleware).
"""

from __future__ import annotations

from datetime import datetime

from developer_brain_ai_shared.kernel.id import ApiKeyId, TenantId, UserId
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from developer_brain_ai_identity.domain.api_key import ApiKey
from developer_brain_ai_identity.domain.repositories import TenantRepository, UserRepository
from developer_brain_ai_identity.domain.tenant import Tenant
from developer_brain_ai_identity.domain.user import User
from developer_brain_ai_identity.domain.value_objects import Email, TenantSlug
from developer_brain_ai_identity.infrastructure.mappers import (
    api_key_from_orm,
    api_key_to_orm,
    tenant_from_orm,
    tenant_to_orm,
    user_from_orm,
    user_to_orm,
)
from developer_brain_ai_identity.infrastructure.orm import ApiKeyORM, TenantORM, UserORM


def _maybe_session(
    ctx_session: AsyncSession | None, factory: async_sessionmaker[AsyncSession]
) -> AsyncSession:
    return ctx_session or factory()


class SqlAlchemyTenantRepository(TenantRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def _open(self) -> AsyncSession:
        return self._factory()

    async def get_by_id(self, tenant_id: TenantId) -> Tenant | None:
        async with self._factory() as s:
            o = await s.get(TenantORM, tenant_id.as_uuid())
            return tenant_from_orm(o) if o else None

    async def get_by_slug(self, slug: TenantSlug) -> Tenant | None:
        async with self._factory() as s:
            stmt = select(TenantORM).where(TenantORM.slug == str(slug))
            r = await s.execute(stmt)
            o = r.scalar_one_or_none()
            return tenant_from_orm(o) if o else None

    async def save(self, tenant: Tenant) -> None:
        async with self._factory() as s:
            orm = tenant_to_orm(tenant)
            await s.merge(orm)
            await s.commit()

    async def slug_exists(self, slug: TenantSlug) -> bool:
        async with self._factory() as s:
            stmt = select(TenantORM.id).where(TenantORM.slug == str(slug)).limit(1)
            r = await s.execute(stmt)
            return r.scalar_one_or_none() is not None


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def get_by_id(self, user_id: UserId) -> User | None:
        async with self._factory() as s:
            o = await s.get(UserORM, user_id.as_uuid())
            return user_from_orm(o) if o else None

    async def get_by_email(self, email: Email) -> User | None:
        async with self._factory() as s:
            stmt = select(UserORM).where(UserORM.email == str(email))
            r = await s.execute(stmt)
            o = r.scalar_one_or_none()
            return user_from_orm(o) if o else None

    async def save(self, user: User) -> None:
        async with self._factory() as s:
            await s.merge(user_to_orm(user))
            await s.commit()

    async def email_exists(self, email: Email) -> bool:
        async with self._factory() as s:
            stmt = select(UserORM.id).where(UserORM.email == str(email)).limit(1)
            r = await s.execute(stmt)
            return r.scalar_one_or_none() is not None


class SqlAlchemyApiKeyRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def get_by_id(self, api_key_id: ApiKeyId) -> ApiKey | None:
        async with self._factory() as s:
            o = await s.get(ApiKeyORM, api_key_id.as_uuid())
            return api_key_from_orm(o) if o else None

    async def get_by_prefix(self, tenant_id: TenantId, prefix: str) -> ApiKey | None:
        async with self._factory() as s:
            stmt = select(ApiKeyORM).where(
                ApiKeyORM.tenant_id == tenant_id.as_uuid(),
                ApiKeyORM.key_prefix == prefix,
                ApiKeyORM.is_revoked.is_(False),
            )
            r = await s.execute(stmt)
            o = r.scalar_one_or_none()
            return api_key_from_orm(o) if o else None

    async def save(self, api_key: ApiKey) -> None:
        async with self._factory() as s:
            await s.merge(api_key_to_orm(api_key))
            await s.commit()

    async def list_by_user(self, user_id: UserId) -> list[ApiKey]:
        async with self._factory() as s:
            stmt = select(ApiKeyORM).where(ApiKeyORM.user_id == user_id.as_uuid())
            r = await s.execute(stmt)
            return [api_key_from_orm(o) for o in r.scalars().all()]

    async def update_last_used(self, api_key_id: ApiKeyId, at: datetime) -> None:

        async with self._factory() as s:
            await s.execute(
                update(ApiKeyORM)
                .where(ApiKeyORM.id == api_key_id.as_uuid())
                .values(last_used_at=at)
            )
            await s.commit()

    async def revoke(self, api_key_id: ApiKeyId) -> None:

        async with self._factory() as s:
            await s.execute(
                update(ApiKeyORM)
                .where(ApiKeyORM.id == api_key_id.as_uuid())
                .values(is_revoked=True)
            )
            await s.commit()


__all__ = [
    "SqlAlchemyApiKeyRepository",
    "SqlAlchemyTenantRepository",
    "SqlAlchemyUserRepository",
]
