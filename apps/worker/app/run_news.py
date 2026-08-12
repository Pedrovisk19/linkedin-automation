"""CLI do cron de news — roda fetch/digest direto, sem arq/redis.

O GitHub Actions e o agendador: cada execucao do workflow chama um desses
modos uma vez. Uso:
    uv run python -m app.run_news fetch     # so coleta RSS/HN/PyPI/GitHub
    uv run python -m app.run_news digest    # fetch + digest (envia p/ Discord)
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.logging import configure_logging
from developer_brain_ai_shared.persistence.session import EngineFactory

from app.config import get_settings
from app.main import build_news_stack

_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


async def _run(mode: str) -> int:
    settings = get_settings()
    configure_logging(level=settings.app_log_level, json_output=settings.app_log_json)

    tenant_raw = settings.news_tenant_id.strip()
    if not tenant_raw:
        print("skipped: NEWS_TENANT_ID nao configurado")
        return 0

    _, session_factory = EngineFactory.build(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
    fetch_uc, digest_uc = build_news_stack(session_factory, prompts_dir=_PROMPTS_DIR)
    tenant_id = TenantId(uuid.UUID(tenant_raw))

    fetch_result = await fetch_uc.execute(tenant_id=tenant_id)
    print(
        "fetch done: "
        f"fetched={fetch_result.fetched} inserted={fetch_result.inserted} "
        f"deduped={fetch_result.deduped} errors={fetch_result.errors}"
    )
    if mode == "fetch":
        return 0

    digest_result = await digest_uc.execute(
        tenant_id=tenant_id,
        ai_writing_tone=settings.ai_writing_tone,
        ai_language=settings.ai_language,
    )
    print(
        "digest done: "
        f"draft_id={digest_result.draft_id} title={digest_result.title!r} "
        f"used_items={digest_result.used_items} "
        f"notified={bool(digest_result.notification_request_id)}"
    )
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "digest"
    if mode not in {"fetch", "digest"}:
        print(f"uso: {sys.argv[0]} (fetch|digest)")
        return 2
    try:
        return asyncio.run(_run(mode))
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
