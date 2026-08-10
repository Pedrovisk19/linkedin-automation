"""Repositorio SQLAlchemy do automation (pipeline_runs)."""

from __future__ import annotations

from datetime import date

from developer_brain_ai_shared.kernel.id import TenantId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from developer_brain_ai_automation.domain.aggregates import PipelineRun
from developer_brain_ai_automation.domain.repositories import PipelineRunRepository
from developer_brain_ai_automation.domain.value_objects import PipelineStep
from developer_brain_ai_automation.infrastructure.mappers import run_from_orm, run_to_orm
from developer_brain_ai_automation.infrastructure.orm import PipelineRunORM


class SqlAlchemyPipelineRunRepository(PipelineRunRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def get_by_key(
        self, *, tenant_id: TenantId, pipeline_date: date, step: PipelineStep
    ) -> PipelineRun | None:
        stmt = select(PipelineRunORM).where(
            PipelineRunORM.tenant_id == tenant_id.as_uuid(),
            PipelineRunORM.pipeline_date == pipeline_date,
            PipelineRunORM.step == step.value,
        )
        async with self._factory() as s:
            o = (await s.execute(stmt)).scalar_one_or_none()
            return run_from_orm(o) if o is not None else None

    async def save(self, run: PipelineRun) -> PipelineRun:
        async with self._factory() as s:
            await s.merge(run_to_orm(run))
            await s.commit()
        return run


__all__ = ["SqlAlchemyPipelineRunRepository"]
