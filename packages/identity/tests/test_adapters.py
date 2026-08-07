"""Testes de infraestrutura do identity: bcrypt + clock (sem DB)."""
from __future__ import annotations

from datetime import UTC, datetime

from developer_brain_ai_identity.infrastructure.adapters import BcryptPasswordHasher, SystemClock


def test_bcrypt_hash_and_verify() -> None:
    h = BcryptPasswordHasher()
    hashed = h.hash("my-strong-pwd-123")
    assert hashed != "my-strong-pwd-123"
    assert hashed.startswith("$2") or hashed.startswith("$2b$")
    assert h.verify("my-strong-pwd-123", hashed) is True


def test_bcrypt_verify_rejects_wrong_password() -> None:
    h = BcryptPasswordHasher()
    hashed = h.hash("right")
    assert h.verify("wrong", hashed) is False


def test_bcrypt_verify_with_invalid_hash_returns_false() -> None:
    h = BcryptPasswordHasher()
    assert h.verify("any", "not-a-real-hash") is False


def test_system_clock_returns_utc_aware() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.tzinfo == UTC
    assert isinstance(now, datetime)