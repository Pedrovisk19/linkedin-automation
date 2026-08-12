"""Mappers entre agregado TelegramRequest e ORM."""

from __future__ import annotations

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_telegram.domain.aggregates import TelegramRequest
from developer_brain_ai_telegram.domain.ids import TelegramRequestId
from developer_brain_ai_telegram.domain.value_objects import ChatId, RequestStatus
from developer_brain_ai_telegram.infrastructure.orm import TelegramRequestORM


def request_to_orm(request: TelegramRequest) -> TelegramRequestORM:
    return TelegramRequestORM(
        id=request.id.as_uuid(),
        tenant_id=request.tenant_id.as_uuid(),
        chat_id=request.chat_id.value,
        draft_id=request.draft_id,
        status=request.status.value,
        created_at=request.timestamps.created_at,
        updated_at=request.timestamps.updated_at,
    )


def request_from_orm(row: TelegramRequestORM) -> TelegramRequest:
    return TelegramRequest(
        id=TelegramRequestId.from_uuid(row.id),
        tenant_id=TenantId.from_uuid(row.tenant_id),
        chat_id=ChatId(row.chat_id),
        draft_id=str(row.draft_id),
        status=RequestStatus(row.status),
        timestamps=Timestamps(created_at=row.created_at, updated_at=row.updated_at),
    )


__all__ = ["request_from_orm", "request_to_orm"]
