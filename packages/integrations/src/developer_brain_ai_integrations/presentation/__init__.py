# integrations :: presentation layer

from developer_brain_ai_identity.presentation.dependencies import CurrentUserDependency
from fastapi import APIRouter

from developer_brain_ai_integrations.application.use_cases import (
    ConnectLinkedIn,
    DisconnectLinkedIn,
    GetLinkedInStatus,
    LinkedInAuthUrlBuilder,
)
from developer_brain_ai_integrations.domain.repositories import LinkedInTokenRepository
from developer_brain_ai_integrations.infrastructure.linkedin_client import (
    HttpLinkedInApiClient,
)
from developer_brain_ai_integrations.presentation.routers import build_router


def mount_integrations(
    *,
    tokens: LinkedInTokenRepository,
    oauth_state_secret: str,
    linkedin_client_id: str,
    linkedin_client_secret: str,
    linkedin_redirect_uri: str,
    current_user_dep: CurrentUserDependency,
) -> APIRouter:
    """Monta o router /integrations/linkedin com DI injetada pelo composition root.

    ``oauth_state_secret`` deve ser a mesma secret do JWT (assina o state do OAuth).
    """

    client = HttpLinkedInApiClient(
        client_id=linkedin_client_id,
        client_secret=linkedin_client_secret,
    )

    return build_router(
        auth_url_builder=LinkedInAuthUrlBuilder(
            oauth_secret=oauth_state_secret,
            client_id=linkedin_client_id,
            redirect_uri=linkedin_redirect_uri,
        ),
        connect_uc=ConnectLinkedIn(tokens, client, redirect_uri=linkedin_redirect_uri),
        status_uc=GetLinkedInStatus(tokens),
        disconnect_uc=DisconnectLinkedIn(tokens),
        oauth_state_secret=oauth_state_secret,
        current_user_dep=current_user_dep,
    )


__all__ = ["mount_integrations"]
