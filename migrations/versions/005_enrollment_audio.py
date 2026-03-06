"""Add enrollment_audio table for model portability.

Revision ID: 005_enrollment_audio
Revises: 004_voice_verification
Create Date: 2026-03-05 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005_enrollment_audio"
down_revision = "004_voice_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enrollment_audio",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("phrase_id", sa.Integer(), nullable=False),
        sa.Column("audio_ogg", sa.LargeBinary(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("enrollment_audio")
