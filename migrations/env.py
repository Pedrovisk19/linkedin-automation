"""Alembic env. Roda migrations async; metadata centralizada em shared.persistence.Base.

Imports ORM dos bounded contexts registrados aqui para que ``target_metadata``
tenha todas as tabelas definidas (autogenerate funcional).
"""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

# Garante import de todos os bounded contexts (packages/*/src) mesmo quando o
# venv nao tem os members instalados como editables (ex.: CI com uv sync).
_REPO_ROOT = Path(__file__).resolve().parents[1]
for _pkg_src in sorted((_REPO_ROOT / "packages").glob("*/src")):
    if str(_pkg_src) not in sys.path:
        sys.path.insert(0, str(_pkg_src))

import developer_brain_ai_automation.infrastructure.orm  # noqa: F401
import developer_brain_ai_content.infrastructure.orm  # noqa: F401
import developer_brain_ai_discord.infrastructure.orm  # noqa: F401
import developer_brain_ai_identity.infrastructure.orm  # noqa: F401
import developer_brain_ai_integrations.infrastructure.orm  # noqa: F401
import developer_brain_ai_journal.infrastructure.orm  # noqa: F401
import developer_brain_ai_news.infrastructure.orm  # noqa: F401
import developer_brain_ai_telegram.infrastructure.orm  # noqa: F401
from alembic import context
from developer_brain_ai_shared.persistence.base import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """URL do banco: prioriza DATABASE_URL (CI/cron), senao alembic.ini."""
    return os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
