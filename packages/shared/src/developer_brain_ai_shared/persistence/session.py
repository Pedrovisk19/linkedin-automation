"""Unit of Work async + tenant RLS.

Cada use_case abre um ``UnitOfWork`` que:

1. Reserva uma conexao async do pool.
2. Emite ``SET LOCAL app.tenant_id = $1`` no BEGIN — habilitando RLS transparente.
3. Expoe ``session`` para os repos.
4. Em commit/rollback, fecha a sessao e dispara eventos do agregado.

Se o tenant nao estiver no ContextVar (job do worker sem request), o caller DEVE
passar ``tenant_id`` explicitamente — falhar alto e melhor que vazar dados de
outro tenant.

Além do UoW, o ``EngineFactory.build`` agora registra um listener de ``begin``
por conexao: se o ContextVar de tenant estiver setado, emite automaticamente
``SET LOCAL app.tenant_id`` na primeira transacao da sessao. Isso faz o RLS
funcionar tambem para repos que abrem sessao propria e para jobs do Arq worker
(que seta o contexto manualmente por job com ``set_tenant_context``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Protocol

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_engine_from_config,
    async_sessionmaker,
)

from developer_brain_ai_shared.events.base import DomainEvent
from developer_brain_ai_shared.events.dispatcher import EventDispatcher
from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.persistence.tenant import (
    get_tenant_context,
    get_tenant_context_optional,
)


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...


class UnitOfWork:
    """Context manager async que aplica RLS por tenant e comita/rollback atomico."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        event_dispatcher: EventDispatcher,
        tenant_id: TenantId | None = None,
    ) -> None:
        self._factory = session_factory
        self._dispatcher = event_dispatcher
        self._explicit_tenant = tenant_id
        self.session: AsyncSession | None = None
        self._events_published = 0

    async def __aenter__(self) -> AsyncSession:
        self.session = self._factory()
        tenant = self._explicit_tenant or get_tenant_context_optional()
        if tenant is None:
            await self.session.close()
            raise RuntimeError("UnitOfWork sem tenant context — chame set_tenant_context")
        # RLS: variavel de sessao. SET LOCAL so vale dentro da transacao atual.
        await self.session.execute(
            __import__("sqlalchemy").text("SET LOCAL app.tenant_id = :tid"),
            {"tid": str(tenant.as_uuid())},
        )
        return self.session

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, _: object
    ) -> None:
        if self.session is None:
            return
        try:
            if exc is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
            self.session = None

    async def commit_and_publish(self, aggregates: list[AggregateRoot]) -> int:
        """Apos commit, coleta eventos dos aggregate roots e publica via dispatcher."""
        if self.session is None:
            raise RuntimeError("UoW closed")
        events: list[DomainEvent] = []
        for agg in aggregates:
            if hasattr(agg, "pull_events"):
                events.extend(agg.pull_events())
        await self.session.commit()
        for ev in events:
            await self._dispatcher.publish(ev)
            self._events_published += 1
        return self._events_published


class EngineFactory:
    """Helper para construir engine + session factory com retry basico e RLS por transacao."""

    @staticmethod
    def build(
        url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_pre_ping: bool = True,
    ) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:

        engine = async_engine_from_config(
            {
                "sqlalchemy.url": url,
                "sqlalchemy.pool_size": pool_size,
                "sqlalchemy.max_overflow": max_overflow,
                "sqlalchemy.pool_pre_ping": pool_pre_ping,
            },
            prefix="sqlalchemy.",
        )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        _bind_tenant_rls(engine)
        return engine, factory


def _begin_handler() -> Callable[[Connection], None]:
    """Retorna handler de ``begin`` que define app.tenant_id quando ha tenant no ContextVar.

    Usa ``set_config`` (funcao SQL) em vez de ``SET LOCAL`` porque oSET LOCAL
    nao suporta parametros bind no protocolo do asyncpg ($1).
    """

    def _set_app_tenant(conn: Connection) -> None:
        current = get_tenant_context_optional()
        if current is not None:
            conn.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": str(current.as_uuid())},
            )

    return _set_app_tenant


def _bind_tenant_rls(
    engine: AsyncEngine, handler: Callable[[Connection], None] | None = None
) -> None:
    """Registra no engine o handler de RLS (dispara no begin de cada conexao).

    Sem contexto de tenant (migrations, leitura de tenants) nada e emitido.
    """
    sync_engine = engine.sync_engine
    event.listen(sync_engine, "begin", handler or _begin_handler())


async def tenant_scoped_session(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Generatro utilitario p/ endpoints que precisam de sessao RLS sem UoW explicito."""
    session = factory()
    tenant = get_tenant_context()
    try:
        await session.execute(
            __import__("sqlalchemy").text("SET LOCAL app.tenant_id = :tid"),
            {"tid": str(tenant.as_uuid())},
        )
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


__all__ = ["EngineFactory", "EventPublisher", "UnitOfWork", "tenant_scoped_session"]
