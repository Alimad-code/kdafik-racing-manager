"""Explicit, versioned user-data export and technical security-artifact retention.

The retention defaults are operational housekeeping values, not legal retention periods.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    EmailActionCode,
    PendingRegistration,
    Season,
    SeasonStage,
    StageSession,
    User,
    UserLegalAcceptance,
    UserSession,
    WebSocketTicket,
)

EXPORT_SCHEMA_VERSION = 1
# Guard list: every current user-owned model is exported or is a security-only exclusion.
EXPORTED_USER_OWNED_MODELS = frozenset(
    {
        "User",
        "Season",
        "SeasonStage",
        "StageSession",
        "Car",
        "CarSetup",
        "BudgetTransaction",
        "SessionResult",
        "UserLegalAcceptance",
    }
)
SECURITY_ONLY_EXCLUDED_MODELS = frozenset(
    {
        "UserSession",
        "EmailActionCode",
        "WebSocketTicket",
        "PendingRegistration",
        "PendingRegistrationAcceptance",
    }
)
SHARED_CATALOG_MODELS = frozenset({"Driver", "Team", "Track", "TrackSegment", "LegalDocument"})
CURRENT_USER_OWNED_MODEL_INVENTORY = EXPORTED_USER_OWNED_MODELS | SECURITY_ONLY_EXCLUDED_MODELS


def build_user_export(session: Session, user_id: UUID) -> dict[str, Any]:
    """Build an explicit export; never serialize ORM models or their secret columns."""
    user = session.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.seasons).selectinload(Season.selected_team),
            selectinload(User.seasons).selectinload(Season.stages).selectinload(SeasonStage.track),
            selectinload(User.seasons)
            .selectinload(Season.stages)
            .selectinload(SeasonStage.sessions)
            .selectinload(StageSession.results),
            selectinload(User.seasons)
            .selectinload(Season.stages)
            .selectinload(SeasonStage.car_setups),
            selectinload(User.seasons).selectinload(Season.cars),
            selectinload(User.seasons).selectinload(Season.budget_transactions),
            selectinload(User.legal_acceptances).selectinload(UserLegalAcceptance.legal_document),
        )
    )
    if user is None:
        raise LookupError("User not found")

    return {
        "schemaVersion": EXPORT_SCHEMA_VERSION,
        "generatedAt": _value(datetime.now(UTC)),
        "account": _record(
            user,
            "id email email_verified_at display_name role active_season_id created_at updated_at",
        ),
        "seasons": [
            _season(season) for season in sorted(user.seasons, key=lambda item: str(item.id))
        ],
        "legalAcceptances": [
            {
                "kind": item.legal_document.kind,
                "version": item.legal_document.version,
                "title": item.legal_document.title,
                "contentSha256": item.legal_document.content_sha256,
                "publicPath": item.legal_document.public_path,
                "acceptedAt": _value(item.accepted_at),
                "source": item.source,
            }
            for item in sorted(user.legal_acceptances, key=lambda item: item.accepted_at)
            if item.legal_document is not None
        ],
    }


def _season(season: Season) -> dict[str, Any]:
    return {
        **_record(
            season,
            "id name year status selected_team_id current_stage_id starting_budget_millions "
            "initial_repair_reserve_millions initial_setup_reserve_millions "
            "finished_at created_at updated_at",
        ),
        "selectedTeam": (
            _record(season.selected_team, "id name short_name base_country")
            if season.selected_team is not None
            else None
        ),
        "cars": [
            _record(
                car,
                "id team_id driver_id slot is_player driver_first_name_snapshot "
                "driver_last_name_snapshot driver_code_snapshot team_name_snapshot "
                "team_short_name_snapshot team_color_snapshot "
                "engine_power aero_efficiency chassis_grip reliability condition wings_setting "
                "suspension_setting gearbox_setting confidence created_at updated_at",
            )
            for car in sorted(season.cars, key=lambda item: item.slot)
        ],
        "budgetTransactions": [
            _record(
                item,
                "id category label amount_millions reserve_applied_millions free_applied_millions "
                "reference_type reference_id created_at",
            )
            for item in sorted(
                season.budget_transactions, key=lambda item: (item.created_at, str(item.id))
            )
        ],
        "stages": [_stage(stage) for stage in season.stages],
    }


def _stage(stage: SeasonStage) -> dict[str, Any]:
    return {
        **_record(stage, "id track_id stage_number weekend_date weather_scenario"),
        "track": _record(stage.track, "id name country") if stage.track is not None else None,
        "carSetups": [
            _record(
                setup,
                "id car_id wings_setting suspension_setting gearbox_setting "
                "setup_band cost_millions "
                "applies_to_session created_at",
            )
            for setup in sorted(stage.car_setups, key=lambda item: str(item.id))
        ],
        "sessions": [
            {
                **_record(item, "id type status sort_order"),
                "results": [
                    _record(
                        result,
                        "id car_id position grid_position best_lap best_lap_number "
                        "max_speed_kph gap laps points status event reason setup_feedback "
                        "engineer_recommendation event_description "
                        "event_severity created_at",
                    )
                    for result in sorted(
                        item.results, key=lambda result: (result.position, str(result.id))
                    )
                ],
            }
            for item in stage.sessions
        ],
    }


def _record(instance: Any, fields: str) -> dict[str, Any]:
    return {_camel(name): _value(getattr(instance, name)) for name in fields.split()}


def _camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.title() for part in rest)


def _value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return (
            value.astimezone(UTC).isoformat()
            if value.tzinfo
            else value.replace(tzinfo=UTC).isoformat()
        )
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_value(item) for item in value]
    return value


class SecurityArtifactCleanup:
    """Bounded deletion of stale security records; safe to call from multiple workers."""

    def __init__(
        self,
        session: Session,
        *,
        batch_size: int = 100,
        revoked_session_days: int = 30,
        unverified_user_days: int = 7,
    ) -> None:
        self.session = session
        self.batch_size = batch_size
        self.revoked_session_days = revoked_session_days
        self.unverified_user_days = unverified_user_days

    def run(self, now: datetime | None = None, *, dry_run: bool = False) -> dict[str, int]:
        now = now or datetime.now(UTC)

        def expired_or_consumed(model: type[Any]) -> Any:
            return or_(model.expires_at <= now, model.consumed_at.is_not(None))

        return {
            "refreshSessions": self._purge(
                UserSession,
                or_(
                    UserSession.expires_at <= now,
                    UserSession.revoked_at <= now - timedelta(days=self.revoked_session_days),
                ),
                dry_run,
            ),
            "emailActionCodes": self._purge(
                EmailActionCode, expired_or_consumed(EmailActionCode), dry_run
            ),
            "websocketTickets": self._purge(
                WebSocketTicket, expired_or_consumed(WebSocketTicket), dry_run
            ),
            "unverifiedUsers": self._purge(
                User,
                User.email_verified_at.is_(None)
                & (User.created_at <= now - timedelta(days=self.unverified_user_days)),
                dry_run,
            ),
            "pendingRegistrations": self._purge(
                PendingRegistration,
                PendingRegistration.confirmed_at.is_(None)
                & (PendingRegistration.expires_at <= now),
                dry_run,
            ),
        }

    def _purge(self, model: type[Any], criterion: Any, dry_run: bool) -> int:
        ids = self.session.scalars(
            select(model.id).where(criterion).order_by(model.id).limit(self.batch_size)
        ).all()
        if ids and not dry_run:
            if model is User:
                # ORM deletion enforces cascade in SQLite test databases as well as production DBs.
                for instance in self.session.scalars(select(User).where(User.id.in_(ids))):
                    self.session.delete(instance)
            else:
                self.session.execute(delete(model).where(model.id.in_(ids)))
        return len(ids)
