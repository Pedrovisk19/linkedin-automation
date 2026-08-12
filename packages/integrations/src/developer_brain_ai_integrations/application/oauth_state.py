"""State do OAuth LinkedIn: assinado com HMAC p/ ataques de tenant spoofing.

O callback do LinkedIn devolve o ``state`` de volta para nos; o estado carrega
o tenant_id assinado, entao o callback sabe em qual tenant salvar o token sem
depender de auth (o browser vai direto na API apos o consentimento).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime

from developer_brain_ai_shared.errors.base import ValidationError
from developer_brain_ai_shared.kernel.id import TenantId

_STATE_TTL_SECONDS = 600


def _sign(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def build_oauth_state(secret: str, tenant_id: TenantId, *, ttl: int = _STATE_TTL_SECONDS) -> str:
    """Gera state assinado com tenant_id + expiracao."""
    body = {
        "tenant_id": str(tenant_id.as_uuid()),
        "exp": int(datetime.now(UTC).timestamp()) + ttl,
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    payload = base64.urlsafe_b64encode(raw).decode()
    return f"{payload}.{_sign(secret, raw)}"


def verify_oauth_state(secret: str, state: str) -> TenantId:
    """Valida assinatura + expiracao do state; devolve o TenantId."""
    try:
        payload_b64, signature = state.split(".", 1)
        raw = base64.urlsafe_b64decode(payload_b64.encode())
    except (ValueError, TypeError) as exc:
        raise ValidationError("state OAuth invalido") from exc
    if not hmac.compare_digest(_sign(secret, raw), signature):
        raise ValidationError("state OAuth nao assinado")
    try:
        body = json.loads(raw)
        exp = int(body["exp"])
        tenant_id = TenantId(body["tenant_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError("state OAuth malformado") from exc
    if datetime.now(UTC).timestamp() > exp:
        raise ValidationError("state OAuth expirado — refaca o fluxo de conexao")
    return tenant_id


__all__ = ["build_oauth_state", "verify_oauth_state"]
