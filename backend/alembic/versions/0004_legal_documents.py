"""Add versioned legal document metadata and user acceptances.

Revision ID: 0004_legal_documents
Revises: 0003_email_action_tokens
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_legal_documents"
down_revision: str | None = "0003_email_action_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "legal_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("public_path", sa.String(length=512), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("required_at_registration", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "kind IN ('privacy_policy', 'personal_data_consent', 'user_agreement')",
            name="ck_legal_documents_kind",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64", name="ck_legal_documents_sha256_length"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_legal_documents_kind_version", "legal_documents", ["kind", "version"], unique=True
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_legal_documents_one_active_kind ON legal_documents (kind) "
        "WHERE retired_at IS NULL"
    )
    op.create_table(
        "user_legal_acceptances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("legal_document_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "source IN ('registration', 'account')", name="ck_user_legal_acceptances_source"
        ),
        sa.ForeignKeyConstraint(
            ["legal_document_id"], ["legal_documents.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_user_legal_acceptances_user_document",
        "user_legal_acceptances",
        ["user_id", "legal_document_id"],
        unique=True,
    )
    op.create_index("ix_user_legal_acceptances_user_id", "user_legal_acceptances", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_legal_acceptances")
    op.drop_index("uq_legal_documents_one_active_kind", table_name="legal_documents")
    op.drop_table("legal_documents")
