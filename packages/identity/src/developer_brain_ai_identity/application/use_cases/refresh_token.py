"""RefreshToken use case: valida refresh, descarta contexto antigo, emite novo par."""
from __future__ import annotations

from developer_brain_ai_identity.application.dto import RefreshInput, TokenOutput
from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.errors.base import UnauthorizedError


class RefreshToken:
    def __init__(self, jwt: JWTService) -> None:
        self._jwt = jwt

    async def execute(self, data: RefreshInput) -> TokenOutput:
        payload = self._jwt.decode(data.refresh_token, expected_type="refresh")
        if payload.is_expired:
            raise UnauthorizedError("refresh token expirado")
        pair = self._jwt.issue_pair(user_id=payload.user_id, tenant_id=payload.tenant_id)
        return TokenOutput(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            expires_at=pair.access_expires_at,
        )


__all__ = ["RefreshToken"]