"""Value objects do modulo telegram: ChatId e RequestStatus."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ChatId:
    """Identificador numerico de chat do Telegram (positivo)."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValueError(f"chat id do telegram invalido: {self.value!r}")

    def __str__(self) -> str:
        return str(self.value)


class RequestStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


__all__ = ["ChatId", "RequestStatus"]
