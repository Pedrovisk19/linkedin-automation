"""Composition helper do journal — monta use cases + router com DI."""

from developer_brain_ai_identity.presentation.dependencies import CurrentUserDependency
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from developer_brain_ai_journal.application.use_cases import (
    CreateJournalEntry,
    DeleteJournalEntry,
    GetJournalEntry,
    ListJournalEntries,
    UpdateJournalEntry,
)
from developer_brain_ai_journal.infrastructure.repositories import SqlAlchemyJournalEntryRepository
from developer_brain_ai_journal.presentation.routers import build_router


def mount_journal(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    current_user_dep: CurrentUserDependency,
) -> APIRouter:
    repo = SqlAlchemyJournalEntryRepository(session_factory)
    create_uc = CreateJournalEntry(repo)
    get_uc = GetJournalEntry(repo)
    list_uc = ListJournalEntries(repo)
    update_uc = UpdateJournalEntry(repo)
    delete_uc = DeleteJournalEntry(repo)
    return build_router(
        create_uc=create_uc,
        get_uc=get_uc,
        list_uc=list_uc,
        update_uc=update_uc,
        delete_uc=delete_uc,
        current_user_dep=current_user_dep,
    )


__all__ = ["mount_journal"]
