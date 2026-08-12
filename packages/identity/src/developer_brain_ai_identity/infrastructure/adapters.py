"""Adapters de infraestrutura para o identity: bcrypt (lib direta, sem passlib) e SystemClock.

Justificativa: passlib quebrou em bcrypt>=4 + Python 3.14
(`module 'bcrypt' has no attribute '__about__'`).
Usar bcrypt direto e mais robusto e remove a dependencia quebrada. Mantemos o
PasswordHasher Protocol — callers nao mudam.
"""

from __future__ import annotations

from datetime import UTC, datetime

import bcrypt

_BCRYPT_MAX_PWD = 72


class BcryptPasswordHasher:
    """Implementacao PasswordHasher via lib bcrypt. Rounds 12."""

    _ROUNDS = 12

    def hash(self, plain: str) -> str:
        salt = bcrypt.gensalt(rounds=self._ROUNDS)
        return bcrypt.hashpw(plain[:_BCRYPT_MAX_PWD].encode("utf-8"), salt).decode("utf-8")

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain[:_BCRYPT_MAX_PWD].encode("utf-8"), hashed.encode("utf-8"))
        except ValueError, TypeError:
            return False


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


__all__ = ["BcryptPasswordHasher", "SystemClock"]
