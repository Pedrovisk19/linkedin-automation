"""Erros de dominio. Traducao para HTTP fica em developer_brain_ai_shared.errors.http."""

from developer_brain_ai_shared.errors.base import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
)

__all__ = [
    "ConflictError",
    "DomainError",
    "ForbiddenError",
    "NotFoundError",
    "RateLimitError",
    "UnauthorizedError",
    "ValidationError",
]
