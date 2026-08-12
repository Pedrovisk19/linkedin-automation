"""Use cases do LinkedIn: connect (OAuth), status e disconnect.

Fluxo de conexao (usuario apos ``/integrations/linkedin/auth-url``):
1. LinkedIn redireciona o browser para nosso callback com ``code`` + ``state``.
2. ``ConnectLinkedIn`` troca o code por access token (e devolve userinfo).
3. Busca member info (userinfo) e persiste LinkedInToken (1 por tenant).

Nota empirica (2026-08): o endpoint de token do LinkedIn rejeita a troca
(HTTP 401 invalid_client) se o corpo incluir ``code_verifier``; o fluxo que
funciona e: code_challenge no authorize + troca SEM verifier no body e SEM
refresh_token (so access ~60 dias) na resposta.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode

from developer_brain_ai_shared.errors.base import NotFoundError
from developer_brain_ai_shared.kernel.id import TenantId

from developer_brain_ai_integrations.application.dto import (
    LinkedInAuthUrlOutput,
    LinkedInStatusOutput,
)
from developer_brain_ai_integrations.application.oauth_state import build_oauth_state
from developer_brain_ai_integrations.application.ports import LinkedInApiClient
from developer_brain_ai_integrations.domain.aggregates import LinkedInToken
from developer_brain_ai_integrations.domain.ids import LinkedInTokenId
from developer_brain_ai_integrations.domain.repositories import LinkedInTokenRepository

_LINKEDIN_AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
_LINKEDIN_SCOPES = "w_member_social openid profile email"


def _pkce_s256_challenge() -> str:
    """Challenge S256 do PKCE (base64url sem padding), so p/ o authorize."""
    verifier = secrets.token_urlsafe(96)
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


class LinkedInAuthUrlBuilder:
    """Monta a URL de autorizacao com state assinado (tenant_id) + code_challenge."""

    def __init__(
        self,
        *,
        oauth_secret: str,
        client_id: str,
        redirect_uri: str,
    ) -> None:
        self._oauth_secret = oauth_secret
        self._client_id = client_id
        self._redirect_uri = redirect_uri

    def execute(self, tenant_id: TenantId) -> LinkedInAuthUrlOutput:
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": _LINKEDIN_SCOPES,
            "state": build_oauth_state(self._oauth_secret, tenant_id),
            "code_challenge": _pkce_s256_challenge(),
            "code_challenge_method": "S256",
        }
        return LinkedInAuthUrlOutput(
            authorization_url=f"{_LINKEDIN_AUTHORIZE_URL}?{urlencode(params)}"
        )


class ConnectLinkedIn:
    """Troca code por access token, busca userinfo e persiste o LinkedInToken do tenant."""

    def __init__(
        self,
        tokens: LinkedInTokenRepository,
        api: LinkedInApiClient,
        *,
        redirect_uri: str,
    ) -> None:
        self._tokens = tokens
        self._api = api
        self._redirect_uri = redirect_uri

    async def execute(self, tenant_id: TenantId, code: str) -> LinkedInStatusOutput:
        data = await self._api.exchange_code(code, self._redirect_uri)
        user = await self._api.get_userinfo(data.access_token)
        token = LinkedInToken(
            id=LinkedInTokenId.new(),
            tenant_id=tenant_id,
            access_token=data.access_token,
            refresh_token=data.refresh_token,
            access_expires_at=data.access_expires_at,
            refresh_expires_at=data.refresh_expires_at,
            member_urn=user.member_urn,
            member_name=user.name,
            timestamps=None,  # type: ignore[arg-type]
        )
        await self._tokens.save(token)
        return _to_status(token)


class GetLinkedInStatus:
    def __init__(self, tokens: LinkedInTokenRepository) -> None:
        self._tokens = tokens

    async def execute(self, tenant_id: TenantId) -> LinkedInStatusOutput:
        token = await self._tokens.get(tenant_id)
        if token is None:
            return LinkedInStatusOutput(connected=False)
        return _to_status(token)


class DisconnectLinkedIn:
    def __init__(self, tokens: LinkedInTokenRepository) -> None:
        self._tokens = tokens

    async def execute(self, tenant_id: TenantId) -> None:
        token = await self._tokens.get(tenant_id)
        if token is None:
            raise NotFoundError("linkedin nao conectado")
        await self._tokens.delete(tenant_id)


def _to_status(token: LinkedInToken) -> LinkedInStatusOutput:
    return LinkedInStatusOutput(
        connected=True,
        member_name=token.member_name,
        member_urn=token.member_urn,
        access_expires_at=token.access_expires_at.isoformat(),
    )


__all__ = [
    "ConnectLinkedIn",
    "DisconnectLinkedIn",
    "GetLinkedInStatus",
    "LinkedInAuthUrlBuilder",
]
