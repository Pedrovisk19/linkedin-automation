"""Agregado LinkedInToken: credenciais OAuth do tenant para a LinkedIn API.

Um tenant tem NO MAXIMO uma conexao LinkedIn (chave primaria = tenant_id).
Guarda access token (+ refresh se o LinkedIn devolver), expiracao e a URN do
membro dono da conexao (urn:li:person:<id>) para publicar posts como o proprio
usuario.

Observacao: para o scope w_member_social + openid, a troca de code do LinkedIn
NORMALMENTE NAO devolve refresh_token (so access, valido ~60 dias) — por isso
refresh_token/refresh_expires_at sao opcionais.

Transicoes de estado:
- ``with_refreshed``: substitui access/refresh apos fluxo de refresh.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from developer_brain_ai_shared.errors.base import ValidationError
from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow

_REFRESH_SKEW_SECONDS = 60


@dataclass(eq=False)
class LinkedInToken(AggregateRoot):
    tenant_id: TenantId
    access_token: str
    access_expires_at: datetime
    refresh_token: str | None = None
    refresh_expires_at: datetime | None = None
    member_urn: str = ""
    member_name: str = ""
    timestamps: Timestamps = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        now = utcnow()
        if not self.tenant_id or not isinstance(self.tenant_id, TenantId):
            raise TypeError("tenant_id deve ser TenantId")
        if not self.access_token or not self.access_token.strip():
            raise ValueError("access_token nao pode ser vazio")
        if self.access_expires_at.tzinfo is None:
            raise ValueError("expiracao precisa ser tz-aware")
        if self.refresh_token is not None:
            if not self.refresh_token.strip():
                raise ValueError("refresh_token nao pode ser vazio")
            if self.refresh_expires_at is None:
                raise ValueError("refresh_token exige refresh_expires_at")
        if self.refresh_expires_at is not None:
            if self.refresh_expires_at.tzinfo is None:
                raise ValueError("expiracao precisa ser tz-aware")
            if self.refresh_expires_at <= now:
                raise ValidationError(
                    "refresh_token ja expirado", details={"tenant_id": str(self.tenant_id)}
                )
        if not self.member_urn or not self.member_urn.strip():
            raise ValueError("member_urn nao pode ser vazio")
        if self.timestamps is None:
            object.__setattr__(self, "timestamps", Timestamps(created_at=now, updated_at=now))

    @property
    def access_is_expired(self) -> bool:
        return datetime.now(UTC) >= self.access_expires_at - timedelta(
            seconds=_REFRESH_SKEW_SECONDS
        )

    def with_refreshed(
        self,
        *,
        access_token: str,
        refresh_token: str | None = None,
        access_expires_at: datetime,
        refresh_expires_at: datetime | None = None,
    ) -> LinkedInToken:
        return LinkedInToken(
            id=self.id,
            tenant_id=self.tenant_id,
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            member_urn=self.member_urn,
            member_name=self.member_name,
            timestamps=self.timestamps.touch(at=utcnow()),
        )


__all__ = ["LinkedInToken"]
