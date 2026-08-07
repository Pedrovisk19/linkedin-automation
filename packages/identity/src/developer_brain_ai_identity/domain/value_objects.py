"""Value objects do modulo identity.

- Email: normaliza lowercase, valida formato basico.
- TenantSlug: [a-z0-9-]{3,40}, sem hifen no inicio/fim.
- PasswordHash: opaco (nao logavel), carrega valor hasheado.
- UserRole: enum ADMIN | MEMBER.
- ApiKeyPlain: valor legivel gerado uma unica vez; prefixo + segredo.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from enum import Enum

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])?$")


class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        v = self.value.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError(f"email invalido: {self.value!r}")
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TenantSlug:
    value: str

    def __post_init__(self) -> None:
        v = self.value.strip().lower()
        if not _SLUG_RE.match(v) or len(v) < 3 or len(v) > 40:
            raise ValueError(f"tenant slug invalido: {self.value!r}")
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PasswordHash:
    """Wrapper opaco p/ hash bcrypt. Nao expoe __repr__ por seguranca."""

    value: str

    def __repr__(self) -> str:
        return "PasswordHash(***)"


@dataclass(frozen=True)
class ApiKeyPlain:
    """Chave legivel gerada uma vez; layout: dba_<prefix>.<secret>."""

    prefix: str
    secret: str

    @classmethod
    def generate(cls) -> ApiKeyPlain:
        prefix = secrets.token_urlsafe(6)
        secret = secrets.token_urlsafe(32)
        return cls(prefix=prefix, secret=secret)

    @property
    def display(self) -> str:
        return f"dba_{self.prefix}.{self.secret}"

    def hashed_value(self) -> str:
        import hashlib

        return hashlib.sha256(self.display.encode()).hexdigest()


__all__ = ["Email", "TenantSlug", "PasswordHash", "UserRole", "ApiKeyPlain"]