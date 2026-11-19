"""create translation_history

Revision ID: 0001
Revises:
Create Date: 2026-11-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "translation_history",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_language", sa.String(length=8), nullable=False),
        sa.Column("target_language", sa.String(length=8), nullable=False),
        sa.Column("model_ids", sa.String(length=200), nullable=False),
        sa.Column("pivot_via", sa.String(length=8), nullable=True),
        sa.Column("input_chars", sa.Integer(), nullable=False),
        sa.Column("output_chars", sa.Integer(), nullable=False),
        sa.Column("segments", sa.Integer(), nullable=False),
        sa.Column("total_ms", sa.Float(), nullable=False),
        sa.Column("warnings", sa.String(length=200), nullable=True),
        sa.Column("text_stored", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("output_text", sa.Text(), nullable=True),
    )
    op.create_index("ix_translation_history_created_at", "translation_history", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_translation_history_created_at", table_name="translation_history")
    op.drop_table("translation_history")
