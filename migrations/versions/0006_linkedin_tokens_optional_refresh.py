"""integrations: refresh_token/refresh_expires_at opcionais em linkedin_tokens.

Revision ID: 0006_linkedin_optional_refresh

A troca de code com scope w_member_social + openid NAO devolve refresh_token
(so access, ~60 dias); as colunas nao podem mais ser NOT NULL.


Revises: 0005_linkedin_tokens
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_linkedin_optional_refresh"
down_revision = "0005_linkedin_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("linkedin_tokens", "refresh_token", existing_type=sa.Text(), nullable=True)
    op.alter_column(
        "linkedin_tokens",
        "refresh_expires_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column("linkedin_tokens", "refresh_token", existing_type=sa.Text(), nullable=False)
    op.alter_column(
        "linkedin_tokens",
        "refresh_expires_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
