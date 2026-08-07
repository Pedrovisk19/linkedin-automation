"""Dominio do modulo identity: aggregates Tenant, User, ApiKey + value objects + ports."""
from developer_brain_ai_identity.domain.api_key import ApiKey
from developer_brain_ai_identity.domain.api_key_repository import ApiKeyRepository
from developer_brain_ai_identity.domain.repositories import TenantRepository, UserRepository
from developer_brain_ai_identity.domain.tenant import Tenant
from developer_brain_ai_identity.domain.user import User
from developer_brain_ai_identity.domain.value_objects import (
    ApiKeyPlain,
    Email,
    PasswordHash,
    TenantSlug,
    UserRole,
)

__all__ = [
    "Tenant",
    "User",
    "ApiKey",
    "Email",
    "TenantSlug",
    "PasswordHash",
    "UserRole",
    "ApiKeyPlain",
    "TenantRepository",
    "UserRepository",
    "ApiKeyRepository",
]