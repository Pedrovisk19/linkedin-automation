"""Agregado DiscordRequest: pedido de aprovacao de publicacao.

Um pedido nasce quando o usuario envia uma mensagem (texto ou audio) e o
sistema gera um draft de LinkedIn. O fluxo fica pendente ate o usuario
aprovar/rejeitar pelos botoes do Discord.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from developer_brain_ai_shared.errors.base import ValidationError
from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow

from developer_brain_ai_discord.domain.ids import DiscordRequestId
from developer_brain_ai_discord.domain.value_objects import ChannelId, RequestStatus


@dataclass(eq=False)
class DiscordRequest(AggregateRoot):
    id: DiscordRequestId
    tenant_id: TenantId
    channel_id: ChannelId
    draft_id: str
    status: RequestStatus = RequestStatus.PENDING
    timestamps: Timestamps = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not self.draft_id or not self.draft_id.strip():
            raise ValueError("draft_id nao pode ser vazio")
        if not isinstance(self.channel_id, ChannelId):
            raise TypeError("channel_id deve ser ChannelId")
        if not isinstance(self.status, RequestStatus):
            raise TypeError("status deve ser RequestStatus")
        if self.timestamps is None:
            now = utcnow()
            object.__setattr__(self, "timestamps", Timestamps(created_at=now, updated_at=now))

    def approve(self) -> None:
        if self.status is not RequestStatus.PENDING:
            raise ValidationError("pedido ja processado", details={"status": self.status.value})
        object.__setattr__(self, "status", RequestStatus.APPROVED)
        _touch(self)

    def reject(self) -> None:
        if self.status is not RequestStatus.PENDING:
            raise ValidationError("pedido ja processado", details={"status": self.status.value})
        object.__setattr__(self, "status", RequestStatus.REJECTED)
        _touch(self)


def _touch(req: DiscordRequest) -> None:
    object.__setattr__(req, "timestamps", req.timestamps.touch(at=utcnow()))


__all__ = ["DiscordRequest"]
