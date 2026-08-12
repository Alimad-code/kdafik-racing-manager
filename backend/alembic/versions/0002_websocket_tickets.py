"""Add one-time websocket tickets.

Revision ID: 0002_websocket_tickets
Revises: 0001_final_schema
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_websocket_tickets"
down_revision: str | None = "0001_final_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "websocket_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_websocket_tickets_ticket_hash", "websocket_tickets", ["ticket_hash"], unique=True
    )
    op.create_index(
        "ix_websocket_tickets_expires_at", "websocket_tickets", ["expires_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_websocket_tickets_expires_at", table_name="websocket_tickets")
    op.drop_index("ix_websocket_tickets_ticket_hash", table_name="websocket_tickets")
    op.drop_table("websocket_tickets")
