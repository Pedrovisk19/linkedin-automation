"""Semeia o tenant default em bancos novos (CI/Neon nao tem init.sql)."""

from __future__ import annotations

import asyncio
import os
import uuid

from developer_brain_ai_shared.persistence.session import EngineFactory
from sqlalchemy import text


async def _main() -> int:
    url = os.environ.get("DATABASE_URL", "").strip()
    tenant_raw = os.environ.get("NEWS_TENANT_ID", "").strip()
    if not url or not tenant_raw:
        print("skipped: DATABASE_URL/NEWS_TENANT_ID nao configurados")
        return 0

    tid = uuid.UUID(tenant_raw)
    slug = os.environ.get("NEWS_TENANT_SLUG", "default").strip()
    name = os.environ.get("NEWS_TENANT_NAME", "Default").strip()

    _, factory = EngineFactory.build(url)
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO tenants (id, slug, name) "
                "VALUES (:id, :slug, :name) ON CONFLICT DO NOTHING"
            ),
            {"id": tid, "slug": slug, "name": name},
        )
        await session.commit()
    print(f"tenant seeded: {tid} (slug={slug})")
    return 0


def main() -> int:
    try:
        return asyncio.run(_main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
