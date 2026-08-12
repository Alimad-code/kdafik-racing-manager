"""Add verified-email state and one-time email action tokens.

Revision ID: 0003_email_action_tokens
Revises: 0002_websocket_tickets
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_email_action_tokens"
down_revision: str | None = "0002_websocket_tickets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "email_action_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "purpose IN ('verification', 'password_reset')", name="ck_email_action_tokens_purpose"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_action_tokens_token_hash", "email_action_tokens", ["token_hash"], unique=True
    )
    op.create_index(
        "ix_email_action_tokens_user_purpose", "email_action_tokens", ["user_id", "purpose"]
    )
    op.create_index("ix_email_action_tokens_expires_at", "email_action_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_email_action_tokens_expires_at", table_name="email_action_tokens")
    op.drop_index("ix_email_action_tokens_user_purpose", table_name="email_action_tokens")
    op.drop_index("ix_email_action_tokens_token_hash", table_name="email_action_tokens")
    op.drop_table("email_action_tokens")
    op.drop_column("users", "email_verified_at")
