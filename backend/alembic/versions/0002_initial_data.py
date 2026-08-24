"""Seed the immutable MVP catalog and published legal-document metadata.

Revision ID: 0002_initial_data
Revises: 0001_initial_schema
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from alembic import op
from app.models import Driver, LegalDocument, Team, Track, TrackSegment
from app.seed.mvp import (
    DRIVERS,
    TEAMS,
    TRACKS,
    svg_path_for_track,
    track_laps,
    track_length_meters,
    track_segments_for_track,
)

revision: str = "0002_initial_data"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEGAL_DOCUMENTS = (
    {
        "id": UUID("1e924d18-4f9a-5f53-8b31-ea7cf5da427c"),
        "kind": "privacy_policy",
        "version": "draft-2026-08-24",
        "title": "Политика обработки персональных данных (проект)",
        "public_path": "/legal/privacy",
        "content_sha256": "69aff3723f54dd3a43aa0d88ffdcbee14735fff44260f810338a7517fe1b6f53",
        "effective_at": datetime(2026, 8, 24, tzinfo=UTC),
        "required_at_registration": True,
    },
    {
        "id": UUID("5d718c8b-4dd2-5c34-a4d8-b0d3e6f5e211"),
        "kind": "personal_data_consent",
        "version": "draft-2026-08-24",
        "title": "Согласие на обработку персональных данных (проект)",
        "public_path": "/legal/consent",
        "content_sha256": "3149fab25d311fa5a78b0e74c7e8e2859be413229ebb1a38f815490bf176d488",
        "effective_at": datetime(2026, 8, 24, tzinfo=UTC),
        "required_at_registration": True,
    },
    {
        "id": UUID("ee327e67-2d6c-5de8-9416-cc5f6b10e809"),
        "kind": "user_agreement",
        "version": "draft-2026-08-24",
        "title": "Пользовательское соглашение (проект)",
        "public_path": "/legal/agreement",
        "content_sha256": "1c3c3c8e20e3379a39c560c0598b65967b20875e76ac3c356fc128a9822886d2",
        "effective_at": datetime(2026, 8, 24, tzinfo=UTC),
        "required_at_registration": True,
    },
)


def upgrade() -> None:
    """Insert a deterministic snapshot without ORM sessions or database reads.

    ``bulk_insert`` renders concrete INSERT statements in Alembic's offline mode,
    so the generated SQL includes the same catalog and legal metadata as an
    online fresh-database upgrade.
    """
    op.bulk_insert(Driver.__table__, DRIVERS)
    op.bulk_insert(Team.__table__, TEAMS)
    op.bulk_insert(Track.__table__, track_rows())
    op.bulk_insert(TrackSegment.__table__, track_segment_rows())
    op.bulk_insert(LegalDocument.__table__, list(LEGAL_DOCUMENTS))


def downgrade() -> None:
    # Initial data is removed together with the initial schema downgrade.
    pass


def track_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for track in TRACKS:
        length_meters = track_length_meters(track)
        rows.append(
            {
                **track,
                "svg_path": svg_path_for_track(track),
                "track_length_meters": length_meters,
                "length_km": (length_meters / Decimal("1000")).quantize(Decimal("0.001")),
                "laps": track_laps(track),
            }
        )
    return rows


def track_segment_rows() -> list[dict[str, object]]:
    return [segment for track in TRACKS for segment in track_segments_for_track(track)]
