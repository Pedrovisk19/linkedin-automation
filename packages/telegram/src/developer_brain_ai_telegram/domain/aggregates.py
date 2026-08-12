"""Agregado TelegramRequest: pedido de aprovacao de publicacao.

Um pedido nasce quando o usuario envia uma mensagem (texto ou audio) e o
sistema gera um draft de LinkedIn. O fluxo fica pendente ate o usuario
aprovar/rejeitar pelos botoes do Telegram.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from developer_brain_ai_shared.errors.base import ValidationError
from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow

from developer_brain_ai_telegram.domain.ids import TelegramRequestId
from developer_brain_ai_telegram.domain.value_objects import ChatId, RequestStatus


@dataclass(eq=False)
class TelegramRequest(AggregateRoot):
    id: TelegramRequestId
    tenant_id: TenantId
    chat_id: ChatId
    draft_id: str
    status: RequestStatus = RequestStatus.PENDING
    timestamps: Timestamps = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not self.draft_id or not self.draft_id.strip():
            raise ValueError("draft_id nao pode ser vazio")
        if not isinstance(self.chat_id, ChatId):
            raise TypeError("chat_id deve ser ChatId")
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


def _touch(req: TelegramRequest) -> None:
    object.__setattr__(req, "timestamps", req.timestamps.touch(at=utcnow()))


__all__ = ["TelegramRequest"]
