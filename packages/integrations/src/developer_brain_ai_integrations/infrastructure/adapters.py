"""Adapters do integrations: LinkedInPostPublisher (usado pelo content module).

Implementa o protocolo ``content.application.ports.LinkedInPostPublisher`` de
forma estrutural (python protocols) — o content nao depende de integrations.
"""

from __future__ import annotations

from datetime import UTC, datetime

from developer_brain_ai_shared.errors.base import ConflictError, IntegrationError
from developer_brain_ai_shared.kernel.id import TenantId

from developer_brain_ai_integrations.application.ports import LinkedInApiClient
from developer_brain_ai_integrations.domain.repositories import LinkedInTokenRepository


class LinkedInPostPublisher:
    """Publica um post no LinkedIn usando o token OAuth do tenant (com refresh)."""

    def __init__(
        self,
        tokens: LinkedInTokenRepository,
        api: LinkedInApiClient,
    ) -> None:
        self._tokens = tokens
        self._api = api

    async def publish(
        self,
        tenant_id: TenantId,
        *,
        text: str,
        hashtags: list[str] | None = None,
    ) -> str:
        token = await self._tokens.get(tenant_id)
        if token is None:
            raise ConflictError(
                "linkedin nao conectado — conecte primeiro em /integrations/linkedin/auth-url"
            )

        if token.access_is_expired:
            if token.refresh_token is None or token.refresh_expires_at is None:
                raise IntegrationError("token linkedin expirado e sem refresh_token")
            if datetime.now(UTC) >= token.refresh_expires_at:
                raise IntegrationError(
                    "refresh_token expirado — reconecte em /integrations/linkedin/auth-url"
                )
            data = await self._api.refresh_tokens(token.refresh_token)
            token = token.with_refreshed(
                access_token=data.access_token,
                refresh_token=data.refresh_token,
                access_expires_at=data.access_expires_at,
                refresh_expires_at=data.refresh_expires_at,
            )
            await self._tokens.save(token)

        commentary = text
        if hashtags:
            commentary = f"{text}\n\n{' '.join(hashtags)}"
        return await self._api.publish_post(token.access_token, token.member_urn, commentary)


__all__ = ["LinkedInPostPublisher"]
