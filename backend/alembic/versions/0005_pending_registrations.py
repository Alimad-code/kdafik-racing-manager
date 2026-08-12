"""Add pending registrations for explicit email confirmation.

Revision ID: 0005_pending_registrations
Revises: 0004_legal_documents
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_pending_registrations"
down_revision = "0004_legal_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_registrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("display_name_normalized", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("confirmation_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["completed_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("display_name_normalized"),
    )
    op.create_index(
        "ix_pending_registrations_token_hash",
        "pending_registrations",
        ["confirmation_token_hash"],
        unique=True,
    )
    op.create_index("ix_pending_registrations_expires_at", "pending_registrations", ["expires_at"])
    op.create_table(
        "pending_registration_acceptances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("registration_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('privacy_policy', 'personal_data_consent', 'user_agreement')",
            name="ck_pending_registration_acceptances_kind",
        ),
        sa.ForeignKeyConstraint(
            ["registration_id"], ["pending_registrations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "registration_id", "kind", name="uq_pending_registration_acceptances_registration_kind"
        ),
    )


def downgrade() -> None:
    op.drop_table("pending_registration_acceptances")
    op.drop_index("ix_pending_registrations_expires_at", table_name="pending_registrations")
    op.drop_index("ix_pending_registrations_token_hash", table_name="pending_registrations")
    op.drop_table("pending_registrations")
