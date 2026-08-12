"""telegram: whatsapp_requests -> telegram_requests (chat_id bigint).

Revision ID: 0008_telegram
Revises: 0007_whatsapp
Create Date: 2026-08-11

A integracao de mensageria migrou do WhatsApp Cloud API para a Telegram Bot
API. A tabela e renomeada e a coluna phone (varchar) vira chat_id (bigint).
A tabela esta vazia (nunca usada em producao); renomeamos para preservar o
RLS/policy e a FK de content_drafts sem recriar a tabela.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_telegram"
down_revision = "0007_whatsapp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("ALTER TABLE whatsapp_requests RENAME TO telegram_requests"))
    bind.execute(sa.text("ALTER TABLE telegram_requests RENAME COLUMN phone TO chat_id"))
    bind.execute(
        sa.text(
            "ALTER TABLE telegram_requests "
            "ALTER COLUMN chat_id TYPE bigint USING chat_id::bigint"
        )
    )
    bind.execute(sa.text("ALTER TABLE telegram_requests RENAME CONSTRAINT whatsapp_requests_pkey TO telegram_requests_pkey"))
    bind.execute(sa.text("ALTER TABLE telegram_requests RENAME CONSTRAINT whatsapp_requests_draft_id_fkey TO telegram_requests_draft_id_fkey"))
    bind.execute(sa.text("ALTER TABLE telegram_requests RENAME CONSTRAINT whatsapp_requests_tenant_id_fkey TO telegram_requests_tenant_id_fkey"))
    bind.execute(sa.text("ALTER INDEX ix_whatsapp_requests_tenant_id RENAME TO ix_telegram_requests_tenant_id"))
    bind.execute(sa.text("ALTER INDEX ix_whatsapp_requests_tenant_id_id RENAME TO ix_telegram_requests_tenant_id_id"))
    bind.execute(sa.text("ALTER INDEX ix_whatsapp_requests_tenant_phone_status RENAME TO ix_telegram_requests_tenant_chat_status"))


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("ALTER TABLE telegram_requests RENAME TO whatsapp_requests"))
    bind.execute(sa.text("ALTER TABLE whatsapp_requests RENAME COLUMN chat_id TO phone"))
    bind.execute(
        sa.text(
            "ALTER TABLE whatsapp_requests "
            "ALTER COLUMN phone TYPE varchar(20) USING phone::varchar(20)"
        )
    )
    bind.execute(sa.text("ALTER TABLE whatsapp_requests RENAME CONSTRAINT telegram_requests_pkey TO whatsapp_requests_pkey"))
    bind.execute(sa.text("ALTER TABLE whatsapp_requests RENAME CONSTRAINT telegram_requests_draft_id_fkey TO whatsapp_requests_draft_id_fkey"))
    bind.execute(sa.text("ALTER TABLE whatsapp_requests RENAME CONSTRAINT telegram_requests_tenant_id_fkey TO whatsapp_requests_tenant_id_fkey"))
    bind.execute(sa.text("ALTER INDEX ix_telegram_requests_tenant_id RENAME TO ix_whatsapp_requests_tenant_id"))
    bind.execute(sa.text("ALTER INDEX ix_telegram_requests_tenant_id_id RENAME TO ix_whatsapp_requests_tenant_id_id"))
    bind.execute(sa.text("ALTER INDEX ix_telegram_requests_tenant_chat_status RENAME TO ix_whatsapp_requests_tenant_phone_status"))