"""Repositorio SQLAlchemy do LinkedInToken."""

from __future__ import annotations

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from developer_brain_ai_integrations.domain.aggregates import LinkedInToken
from developer_brain_ai_integrations.domain.ids import LinkedInTokenId
from developer_brain_ai_integrations.domain.repositories import LinkedInTokenRepository
from developer_brain_ai_integrations.infrastructure.orm import LinkedInTokenORM


class SqlAlchemyLinkedInTokenRepository(LinkedInTokenRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def get(self, tenant_id: TenantId) -> LinkedInToken | None:
        stmt = select(LinkedInTokenORM).where(LinkedInTokenORM.tenant_id == tenant_id.as_uuid())
        async with self._factory() as s:
            o = (await s.execute(stmt)).scalar_one_or_none()
            return _from_orm(o) if o is not None else None

    async def save(self, token: LinkedInToken) -> None:
        if token.id is None:
            object.__setattr__(token, "id", LinkedInTokenId.new())
        async with self._factory() as s:
            await s.merge(_to_orm(token))
            await s.commit()

    async def delete(self, tenant_id: TenantId) -> None:
        async with self._factory() as s:
            await s.execute(
                delete(LinkedInTokenORM).where(LinkedInTokenORM.tenant_id == tenant_id.as_uuid())
            )
            await s.commit()


def _to_orm(t: LinkedInToken) -> LinkedInTokenORM:
    return LinkedInTokenORM(
        id=t.id.as_uuid(),
        tenant_id=t.tenant_id.as_uuid(),
        access_token=t.access_token,
        refresh_token=t.refresh_token,
        access_expires_at=t.access_expires_at,
        refresh_expires_at=t.refresh_expires_at,
        member_urn=t.member_urn,
        member_name=t.member_name,
        created_at=t.timestamps.created_at,
        updated_at=t.timestamps.updated_at,
    )


def _from_orm(o: LinkedInTokenORM) -> LinkedInToken:
    return LinkedInToken(
        id=LinkedInTokenId.from_uuid(o.id),
        tenant_id=TenantId(o.tenant_id),
        access_token=o.access_token,
        refresh_token=o.refresh_token,
        access_expires_at=o.access_expires_at,
        refresh_expires_at=o.refresh_expires_at,
        member_urn=o.member_urn,
        member_name=o.member_name,
        timestamps=Timestamps(created_at=o.created_at, updated_at=o.updated_at),
    )


__all__ = ["SqlAlchemyLinkedInTokenRepository"]
