"""Fakes/in-memory das portas do automation para os testes de use case."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from developer_brain_ai_automation.domain.aggregates import PipelineRun
from developer_brain_ai_automation.domain.value_objects import PipelineStep
from developer_brain_ai_shared.kernel.id import TenantId


class FakeTenantLister:
    def __init__(self, tenants: list[TenantId]) -> None:
        self._tenants = tenants

    async def list_active(self) -> list[TenantId]:
        return list(self._tenants)


class FakeEntryReader:
    def __init__(self, by_tenant: dict[str, list[dict]] | None = None) -> None:
        self._by = by_tenant or {}

    def set_entries(self, tenant: TenantId, entries: list[dict]) -> None:
        self._by[str(tenant.as_uuid())] = entries

    async def list_entries(self, *, tenant_id: TenantId, day: date) -> list[dict]:
        return list(self._by.get(str(tenant_id.as_uuid()), []))


class FakeSummaryGenerator:
    def __init__(self, *, fail: bool = False, error: Exception | None = None) -> None:
        self.calls: list[tuple[TenantId, list[dict]]] = []
        self._fail = fail
        self._error = error
        self.next_output: str | None = None

    async def generate(self, *, tenant_id: TenantId, entries: list[dict]) -> str:
        self.calls.append((tenant_id, entries))
        if self._fail:
            raise self._error or RuntimeError("summary boom")
        return self.next_output or f"resumo de {len(entries)} entries"


class FakeLinkedInDraftCreator:
    def __init__(self, *, fail: bool = False, error: Exception | None = None) -> None:
        self.calls: list[tuple[TenantId, list[dict]]] = []
        self._fail = fail
        self._error = error

    async def create(self, *, tenant_id: TenantId, entries: list[dict]) -> str:
        self.calls.append((tenant_id, entries))
        if self._fail:
            raise self._error or RuntimeError("draft falhou")
        return "draft-1"


class FakeQueuer:
    def __init__(self) -> None:
        self.items: list[tuple[str, datetime]] = []

    async def enqueue(self, *, tenant_id: TenantId, draft_id: str, scheduled_for: datetime) -> None:
        self.items.append((draft_id, scheduled_for))


class FakePipelineRunRepository:
    def __init__(self) -> None:
        self.runs: list[PipelineRun] = []
        self.saved: list[PipelineRun] = []

    async def get_by_key(
        self, *, tenant_id: TenantId, pipeline_date: date, step: PipelineStep
    ) -> PipelineRun | None:
        for r in self.runs:
            if r.tenant_id == tenant_id and r.pipeline_date == pipeline_date and r.step == step:
                return r
        return None

    async def save(self, run: PipelineRun) -> PipelineRun:
        self.saved.append(run)
        for i, r in enumerate(self.runs):
            if (
                r.tenant_id == run.tenant_id
                and r.pipeline_date == run.pipeline_date
                and r.step == run.step
            ):
                self.runs[i] = run
                return run
        self.runs.append(run)
        return run

    def count(self, step: PipelineStep) -> int:
        return sum(1 for r in self.runs if r.step == step)


class FakeTenantExecutor:
    """Captura o tenant corrente durante a execucao (valida contexto RLS)."""

    def __init__(self) -> None:
        self.seen: list[TenantId | None] = []
        self._hook: Callable[[], TenantId | None] | None = None

    def set_hook(self, hook: Callable[[], TenantId | None]) -> None:
        self._hook = hook

    async def probe(self) -> None:
        if self._hook is not None:
            self.seen.append(self._hook())


__all__ = [
    "FakeEntryReader",
    "FakeLinkedInDraftCreator",
    "FakePipelineRunRepository",
    "FakeQueuer",
    "FakeSummaryGenerator",
    "FakeTenantLister",
]
