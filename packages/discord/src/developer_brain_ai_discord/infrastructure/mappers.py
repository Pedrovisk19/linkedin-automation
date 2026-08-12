"""Mappers entre agregado DiscordRequest e ORM."""

from __future__ import annotations

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_discord.domain.aggregates import DiscordRequest
from developer_brain_ai_discord.domain.ids import DiscordRequestId
from developer_brain_ai_discord.domain.value_objects import ChannelId, RequestStatus
from developer_brain_ai_discord.infrastructure.orm import DiscordRequestORM


def request_to_orm(request: DiscordRequest) -> DiscordRequestORM:
    return DiscordRequestORM(
        id=request.id.as_uuid(),
        tenant_id=request.tenant_id.as_uuid(),
        channel_id=request.channel_id.value,
        draft_id=request.draft_id,
        status=request.status.value,
        created_at=request.timestamps.created_at,
        updated_at=request.timestamps.updated_at,
    )


def request_from_orm(row: DiscordRequestORM) -> DiscordRequest:
    return DiscordRequest(
        id=DiscordRequestId.from_uuid(row.id),
        tenant_id=TenantId.from_uuid(row.tenant_id),
        channel_id=ChannelId(row.channel_id),
        draft_id=str(row.draft_id),
        status=RequestStatus(row.status),
        timestamps=Timestamps(created_at=row.created_at, updated_at=row.updated_at),
    )


__all__ = ["request_from_orm", "request_to_orm"]
