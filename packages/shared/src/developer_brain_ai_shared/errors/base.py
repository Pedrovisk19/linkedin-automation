"""Hierarquia de erros de domínio.

Domain NUNCA conhece HTTP. Esta camada traduz para status codes na presentation.
Convencao de nomeclatura:
- DomainError: base abstrata.
- NotFoundError: recurso nao existe.
- ConflictError: violacao de restricao (unique, conflito de estado).
- ValidationError: falha de invariantes de dominio.
- UnauthorizedError: auth faltante.
- ForbiddenError: auth presente mas sem permissao.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base de erros de dominio. Carrega codigo estavel p/ i18n/client."""

    code: str = "domain_error"
    http_status: int = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


class NotFoundError(DomainError):
    code = "not_found"
    http_status = 404


class ConflictError(DomainError):
    code = "conflict"
    http_status = 409


class ValidationError(DomainError):
    code = "validation_error"
    http_status = 422


class UnauthorizedError(DomainError):
    code = "unauthorized"
    http_status = 401


class ForbiddenError(DomainError):
    code = "forbidden"
    http_status = 403


class RateLimitError(DomainError):
    code = "rate_limited"
    http_status = 429


class IntegrationError(DomainError):
    """Falha em integracao externa (LinkedIn, GitHub, ...)."""

    code = "integration_error"
    http_status = 502


__all__ = [
    "ConflictError",
    "DomainError",
    "ForbiddenError",
    "NotFoundError",
    "RateLimitError",
    "UnauthorizedError",
    "ValidationError",
]
