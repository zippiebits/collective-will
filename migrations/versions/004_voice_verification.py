"""Add voice verification columns to users table.

Revision ID: 004_voice_verification
Revises: 003_ip_signup_log
Create Date: 2026-03-04 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004_voice_verification"
down_revision = "003_ip_signup_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("voice_enrolled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("voice_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("voice_embedding", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("voice_model_version", sa.String(128), nullable=True))

    # Partial index for enrolled users (useful for stats queries)
    op.create_index(
        "ix_users_voice_enrolled_at",
        "users",
        ["voice_enrolled_at"],
        postgresql_where=sa.text("voice_enrolled_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_voice_enrolled_at", table_name="users")
    op.drop_column("users", "voice_model_version")
    op.drop_column("users", "voice_embedding")
    op.drop_column("users", "voice_verified_at")
    op.drop_column("users", "voice_enrolled_at")
