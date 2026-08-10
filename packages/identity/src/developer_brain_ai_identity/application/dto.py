"""DTOs (Pydantic) do modulo identity. Camada de comunicação use_case <-> presentation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from developer_brain_ai_identity.domain.value_objects import UserRole


class RegisterTenantInput(BaseModel):
    tenant_slug: str = Field(
        min_length=3, max_length=40, pattern=r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"
    )
    tenant_name: str = Field(min_length=1, max_length=120)
    admin_email: EmailStr
    admin_name: str = Field(min_length=1, max_length=120)
    admin_password: str = Field(min_length=8, max_length=128)


class RegisterTenantOutput(BaseModel):
    tenant_id: str
    user_id: str
    email: str


class LoginInput(BaseModel):
    tenant_slug: str
    email: EmailStr
    password: str


class TokenOutput(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: datetime


class RefreshInput(BaseModel):
    refresh_token: str


class CreateApiKeyInput(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    expires_at: datetime | None = None


class CreateApiKeyOutput(BaseModel):
    api_key_id: str
    label: str
    key_display: str  # mostrado UMA vez apenas
    prefix: str
    expires_at: datetime | None


class ApiKeyView(BaseModel):
    id: str
    label: str
    prefix: str
    expires_at: datetime | None
    last_used_at: datetime | None
    is_revoked: bool


__all__ = [
    "ApiKeyView",
    "CreateApiKeyInput",
    "CreateApiKeyOutput",
    "LoginInput",
    "RefreshInput",
    "RegisterTenantInput",
    "RegisterTenantOutput",
    "TokenOutput",
    "UserRole",
]
