"""Set final legal documents effective from midnight Moscow time.

Revision ID: 0003_correct_legal_effective_time
Revises: 0002_initial_data
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from alembic import op
from app.models import LegalDocument

revision: str = "0003_correct_legal_effective_time"
down_revision: str | None = "0002_initial_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EFFECTIVE_AT = datetime(2026, 8, 24, 21, tzinfo=UTC)


def upgrade() -> None:
    op.execute(
        LegalDocument.__table__.update()
        .where(LegalDocument.version == "2026-08-25")
        .values(effective_at=_EFFECTIVE_AT)
    )


def downgrade() -> None:
    op.execute(
        LegalDocument.__table__.update()
        .where(LegalDocument.version == "2026-08-25")
        .values(effective_at=datetime(2026, 8, 25, tzinfo=UTC))
    )
