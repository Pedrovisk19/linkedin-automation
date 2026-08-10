"""Routers do modulo journal — endpoints autenticados /journals.

NAO usa `from __future__ import annotations` (ADR-0012).
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from developer_brain_ai_journal.application.dto import (
    CreateJournalEntryInput,
    JournalEntryOut,
    UpdateJournalEntryInput,
)
from developer_brain_ai_journal.application.use_cases import (
    CreateJournalEntry,
    DeleteJournalEntry,
    GetJournalEntry,
    ListJournalEntries,
    UpdateJournalEntry,
)


def build_router(
    *,
    create_uc: CreateJournalEntry,
    get_uc: GetJournalEntry,
    list_uc: ListJournalEntries,
    update_uc: UpdateJournalEntry,
    delete_uc: DeleteJournalEntry,
    current_user_dep,
) -> APIRouter:
    from developer_brain_ai_identity.presentation.dependencies import CurrentUser

    UserDep = Annotated[CurrentUser, Depends(current_user_dep)]
    router = APIRouter(prefix="/journals", tags=["journal"])

    @router.post("", response_model=JournalEntryOut, status_code=201)
    async def create(current: UserDep, body: CreateJournalEntryInput) -> JournalEntryOut:
        return await create_uc.execute(current.tenant_id, body)

    @router.get("", response_model=list[JournalEntryOut])
    async def list_entries(
        current: UserDep,
        since: Annotated[date | None, Query()] = None,
        until: Annotated[date | None, Query()] = None,
        tag: Annotated[str | None, Query()] = None,
        technology: Annotated[str | None, Query()] = None,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    ) -> list[JournalEntryOut]:
        items, _ = await list_uc.execute(
            current.tenant_id,
            since=since,
            until=until,
            tag=tag,
            technology=technology,
            page=page,
            page_size=page_size,
        )
        return items

    @router.get("/{entry_id}", response_model=JournalEntryOut)
    async def get_one(current: UserDep, entry_id: str) -> JournalEntryOut:
        return await get_uc.execute(current.tenant_id, entry_id)

    @router.patch("/{entry_id}", response_model=JournalEntryOut)
    async def update(
        current: UserDep, entry_id: str, body: UpdateJournalEntryInput
    ) -> JournalEntryOut:
        return await update_uc.execute(current.tenant_id, entry_id, body)

    @router.delete("/{entry_id}", status_code=204)
    async def delete_one(current: UserDep, entry_id: str) -> None:
        await delete_uc.execute(current.tenant_id, entry_id)

    return router


__all__ = ["build_router"]
