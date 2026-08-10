"""Token JWT (access + refresh) — possivel testar sem ler globals.

``JWTService`` recebe secret/algo/TTLs via construtor — assinatura estavel e
injetavel. Claims carregam ``sub`` (user_id), ``tenant_id``, ``typ`` (access|refresh),
``iat``, ``exp``. Refresh nao cabe em access e vice-versa (checagem em decode).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from jose import JWTError, jwt

from developer_brain_ai_shared.errors.base import UnauthorizedError
from developer_brain_ai_shared.kernel.id import TenantId, UserId

TokenType = Literal["access", "refresh"]


@dataclass(frozen=True)
class TokenPayload:
    user_id: UserId
    tenant_id: TenantId
    token_type: TokenType
    issued_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    access_expires_at: datetime


class JWTService:
    """Encoder/decoder para JWTs HS256. Stateless — seguro de reusar em DI singleton."""

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_ttl_seconds: int = 900,
        refresh_ttl_seconds: int = 2_592_000,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("jwt_secret deve ter ao menos 32 caracteres")
        self._secret = secret
        self._algo = algorithm
        self._access_ttl = access_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds

    def issue_pair(self, user_id: UserId, tenant_id: TenantId) -> TokenPair:
        now = datetime.now(UTC)
        access_exp = now + timedelta(seconds=self._access_ttl)
        refresh_exp = now + timedelta(seconds=self._refresh_ttl)
        access = self._encode(user_id, tenant_id, "access", now, access_exp)
        refresh = self._encode(user_id, tenant_id, "refresh", now, refresh_exp)
        return TokenPair(access_token=access, refresh_token=refresh, access_expires_at=access_exp)

    def decode(self, token: str, expected_type: TokenType) -> TokenPayload:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self._algo])
        except JWTError as exc:
            raise UnauthorizedError("token invalido") from exc

        typ = claims.get("typ")
        if typ != expected_type:
            raise UnauthorizedError(f"esperado token {expected_type}, recebido {typ}")

        try:
            user_id = UserId(claims["sub"])
            tenant_id = TenantId(claims["tenant_id"])
            iat = datetime.fromtimestamp(claims["iat"], tz=UTC)
            exp = datetime.fromtimestamp(claims["exp"], tz=UTC)
        except (KeyError, ValueError, TypeError) as exc:
            raise UnauthorizedError("claims malformados") from exc

        return TokenPayload(
            user_id=user_id, tenant_id=tenant_id, token_type=typ, issued_at=iat, expires_at=exp
        )

    def _encode(
        self,
        user_id: UserId,
        tenant_id: TenantId,
        typ: TokenType,
        issued_at: datetime,
        expires_at: datetime,
    ) -> str:
        claims = {
            "sub": str(user_id.as_uuid()),
            "tenant_id": str(tenant_id.as_uuid()),
            "typ": typ,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(claims, self._secret, algorithm=self._algo)


__all__ = ["JWTService", "TokenPair", "TokenPayload", "TokenType"]
