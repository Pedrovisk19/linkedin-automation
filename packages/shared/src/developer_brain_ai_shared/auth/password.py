"""Passlib bcrypt wrapper. Trocavel por Argon2 sem tocar callers (Dependency Inversion).

O PasswordHasher e uma interface (Protocol); a implementacao concreta
``BcryptPasswordHasher`` vive em infrastructure. Mantemos o Protocol aqui para
que use_cases dependam da abstracao, nao de passlib.
"""
from __future__ import annotations

from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, plain: str) -> str: ...
    def verify(self, plain: str, hashed: str) -> bool: ...


__all__ = ["PasswordHasher"]