"""Aggregate root User."""

from __future__ import annotations

from dataclasses import dataclass

from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId, UserId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_identity.domain.events import (
    UserLoggedIn,
    UserRegistered,
    UserSuspended,
)
from developer_brain_ai_identity.domain.value_objects import Email, PasswordHash, UserRole


@dataclass(eq=False)
class User(AggregateRoot):
    id: UserId
    tenant_id: TenantId
    email: Email
    name: str
    role: UserRole
    password_hash: PasswordHash
    is_active: bool
    timestamps: Timestamps

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("user name nao pode ser vazio")
        if len(self.name) > 120:
            raise ValueError("user name excede 120 caracteres")
        if not isinstance(self.role, UserRole):
            raise TypeError("role deve ser UserRole")

    @classmethod
    def register(
        cls,
        *,
        id: UserId,
        tenant_id: TenantId,
        email: Email,
        name: str,
        password_hash: PasswordHash,
        role: UserRole,
        timestamps: Timestamps,
    ) -> User:
        user = cls(
            id=id,
            tenant_id=tenant_id,
            email=email,
            name=name,
            role=role,
            password_hash=password_hash,
            is_active=True,
            timestamps=timestamps,
        )
        user.record_event(UserRegistered(tenant_id=tenant_id, user_id=id, email=str(email)))
        return user

    def suspend(self) -> None:
        if not self.is_active:
            return
        object.__setattr__(self, "is_active", False)
        self.record_event(UserSuspended(tenant_id=self.tenant_id, user_id=self.id))

    def mark_logged_in(self) -> None:
        self.record_event(UserLoggedIn(tenant_id=self.tenant_id, user_id=self.id))


__all__ = ["User"]
