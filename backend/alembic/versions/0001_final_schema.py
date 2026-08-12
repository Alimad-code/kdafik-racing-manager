"""Final normalized schema baseline.

Revision ID: 0001_final_schema
Revises:
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import app.models  # noqa: F401
from alembic import op
from app.db.base import Base
from sqlalchemy import MetaData

revision: str = "0001_final_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LATER_MIGRATION_TABLES = {
    "websocket_tickets",
    "email_action_tokens",
    "legal_documents",
    "user_legal_acceptances",
    "pending_registrations",
    "pending_registration_acceptances",
}


def baseline_metadata() -> MetaData:
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)
    for table in Base.metadata.sorted_tables:
        if table.name in LATER_MIGRATION_TABLES:
            continue
        copied_table = table.to_metadata(metadata)
        if table.name == "users" and "email_verified_at" in copied_table.c:
            copied_table._columns.remove(copied_table.c.email_verified_at)
    return metadata


def upgrade() -> None:
    baseline_metadata().create_all(op.get_bind())


def downgrade() -> None:
    baseline_metadata().drop_all(op.get_bind())
