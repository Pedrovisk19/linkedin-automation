"""Cliente HTTP concreto da LinkedIn API (httpx).

OAuth2 do LinkedIn (Marketing API):
- Authorization: ``/oauth/v2/authorization`` (scope w_member_social + openid).
- Token: ``POST /oauth/v2/accessToken`` (grant_type=authorization_code | refresh_token).
- Member info: ``GET /v2/userinfo`` (OpenID) -> sub == person id.
- Post: ``POST /rest/posts`` (Member Posts API, header LinkedIn-Version + x-restli).

Erros HTTP nao-2xx viram ``IntegrationError`` (500) com detalhes do corpo.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx
from developer_brain_ai_shared.errors.base import IntegrationError, ValidationError
from developer_brain_ai_shared.logging import get_logger

from developer_brain_ai_integrations.application.ports import (
    LinkedInApiClient,
    LinkedInTokenData,
    LinkedInUserInfo,
)

_TOKEN_ENDPOINT = "https://www.linkedin.com/oauth/v2/accessToken"
_USERINFO_ENDPOINT = "https://api.linkedin.com/v2/userinfo"
_RAW_POST_ENDPOINT = "https://api.linkedin.com/rest/posts"
_LINKEDIN_API_VERSION = "202604"
_COMMENTARY_MAX = 3000


def _parse_token_response(data: dict[str, Any]) -> LinkedInTokenData:
    access = data.get("access_token")
    if not access:
        get_logger().warning(
            "linkedin token response incompleta",
            chaves_presentes=sorted(data.keys()),
            body=str(data)[:800],
        )
        raise ValidationError(
            "resposta de token do LinkedIn incompleta",
            details={"chaves_presentes": sorted(data.keys())},
        )
    now = datetime.now(UTC)
    refresh = data.get("refresh_token")
    expires_in = int(data.get("expires_in", 0) or 0)
    refresh_in = int(
        data.get("refresh_token_expires_in", 0) or data.get("refresh_token_expires", 0) or 0
    )
    return LinkedInTokenData(
        access_token=access,
        access_expires_at=now + timedelta(seconds=expires_in),
        refresh_token=refresh if isinstance(refresh, str) else None,
        refresh_expires_at=now + timedelta(seconds=refresh_in) if refresh_in else None,
    )


class HttpLinkedInApiClient(LinkedInApiClient):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        timeout: float = 15.0,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout

    async def exchange_code(self, code: str, redirect_uri: str) -> LinkedInTokenData:
        data = await self._call_token(
            grant_type="authorization_code",
            extra={"code": code, "redirect_uri": redirect_uri},
        )
        return _parse_token_response(data)

    async def refresh_tokens(self, refresh_token: str) -> LinkedInTokenData:
        data = await self._call_token(
            grant_type="refresh_token",
            extra={"refresh_token": refresh_token},
        )
        return _parse_token_response(data)

    async def get_userinfo(self, access_token: str) -> LinkedInUserInfo:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(_USERINFO_ENDPOINT, headers=headers)
        _raise_for_status(r, "userinfo")
        body = r.json()
        sub = body.get("sub")
        if not sub:
            raise ValidationError("userinfo do LinkedIn sem sub")
        return LinkedInUserInfo(
            member_urn=f"urn:li:person:{sub}",
            name=str(body.get("name") or sub),
        )

    async def publish_post(self, access_token: str, member_urn: str, commentary: str) -> str:
        """Cria post publico (Main Feed) e devolve a URN do post criado."""
        if len(commentary) > _COMMENTARY_MAX:
            raise ValidationError(f"post excede {_COMMENTARY_MAX} caracteres")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": _LINKEDIN_API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }
        payload = {
            "author": member_urn,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(_RAW_POST_ENDPOINT, headers=headers, json=payload)
        _raise_for_status(r, "create post")
        urn_raw = r.headers.get("x-restli-id")
        if not isinstance(urn_raw, str):
            raise ValidationError("criacao de post nao devolveu x-restli-id")
        return urn_raw

    async def _call_token(self, *, grant_type: str, extra: dict[str, Any]) -> dict[str, Any]:
        form = {
            "grant_type": grant_type,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            **extra,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(_TOKEN_ENDPOINT, data=form)
        _raise_for_status(r, "oauth token")
        return cast(dict[str, Any], r.json())


def _raise_for_status(r: httpx.Response, action: str) -> None:
    if r.status_code < 400:
        return
    detail = ""
    with contextlib.suppress(Exception):
        detail = r.text[:500]
    raise IntegrationError(
        f"linkedin falhou em {action} (HTTP {r.status_code})",
        details={"status": r.status_code, "body": detail},
    )


__all__ = ["HttpLinkedInApiClient"]
