"""Repositorio SQLAlchemy de TelegramRequest.

Atencao: usa ``Session.merge`` para nao regenerar o id em upsert (bug historico
do monorepo: gerar uuid novo no save criava duplicatas). O RLS vem do
begin-handler do engine (ContextVar de tenant), como nos demais repos.
"""

from __future__ import annotations

from developer_brain_ai_shared.kernel.id import TenantId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from developer_brain_ai_telegram.domain.aggregates import TelegramRequest
from developer_brain_ai_telegram.domain.repositories import TelegramRequestRepository
from developer_brain_ai_telegram.infrastructure.mappers import (
    request_from_orm,
    request_to_orm,
)
from developer_brain_ai_telegram.infrastructure.orm import TelegramRequestORM


class SqlAlchemyTelegramRequestRepository(TelegramRequestRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def get_by_id(
        self, tenant_id: TenantId, request_id: object
    ) -> TelegramRequest | None:
        async with self._factory() as session:
            row = await session.get(TelegramRequestORM, str(request_id))
            if row is None or row.tenant_id != tenant_id.as_uuid():
                return None
            return request_from_orm(row)

    async def get_pending_by_chat(
        self, tenant_id: TenantId, chat_id: int
    ) -> TelegramRequest | None:
        async with self._factory() as session:
            stmt = (
                select(TelegramRequestORM)
                .where(
                    TelegramRequestORM.tenant_id == tenant_id.as_uuid(),
                    TelegramRequestORM.chat_id == chat_id,
                    TelegramRequestORM.status == "pending",
                )
                .order_by(TelegramRequestORM.created_at.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).scalars().first()
            return request_from_orm(row) if row is not None else None

    async def save(self, request: TelegramRequest) -> None:
        async with self._factory() as session:
            await session.merge(request_to_orm(request))
            await session.commit()


__all__ = ["SqlAlchemyTelegramRequestRepository"]
