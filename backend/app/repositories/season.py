from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.constants import DEV_USER_ID
from app.domain.enums import UserRole
from app.models import (
    BudgetTransaction,
    Car,
    Driver,
    Season,
    SeasonStage,
    Team,
    Track,
    User,
)


class SeasonRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_dev_user(self) -> User:
        user = self.session.get(User, DEV_USER_ID)
        if user is not None:
            return user

        user = User(
            id=DEV_USER_ID,
            display_name="Dev Team Principal",
            display_name_normalized="dev team principal",
            email="dev@kdafik-racing-manager.local",
            password_hash="legacy-dev-user",
            role=UserRole.TEAM_PRINCIPAL,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def get_for_user(self, season_id: UUID, user_id: UUID) -> Season | None:
        statement = (
            select(Season)
            .where(Season.id == season_id, Season.user_id == user_id)
            .options(
                selectinload(Season.selected_team),
                selectinload(Season.stages).selectinload(SeasonStage.track),
                selectinload(Season.cars).selectinload(Car.driver),
                selectinload(Season.cars).selectinload(Car.team),
                selectinload(Season.stages).selectinload(SeasonStage.sessions),
                selectinload(Season.budget_transactions),
            )
        )
        return self.session.scalar(statement)

    def list_for_user(self, user_id: UUID) -> list[Season]:
        statement = (
            select(Season)
            .where(Season.user_id == user_id)
            .order_by(Season.created_at.desc())
            .options(
                selectinload(Season.selected_team),
                selectinload(Season.stages).selectinload(SeasonStage.track),
                selectinload(Season.stages).selectinload(SeasonStage.sessions),
            )
        )
        return list(self.session.scalars(statement))

    def list_tracks_by_ids(self, track_ids: set[str]) -> list[Track]:
        statement = select(Track).where(Track.id.in_(track_ids))
        return list(self.session.scalars(statement))

    def list_active_drivers_by_ids(self, driver_ids: list[str]) -> list[Driver]:
        statement = select(Driver).where(Driver.id.in_(driver_ids), Driver.is_active.is_(True))
        return list(self.session.scalars(statement))

    def list_active_drivers(self) -> list[Driver]:
        statement = select(Driver).where(Driver.is_active.is_(True))
        return list(self.session.scalars(statement))

    def list_active_teams(self) -> list[Team]:
        statement = select(Team).where(Team.is_active.is_(True))
        return list(self.session.scalars(statement))

    def get_active_team(self, team_id: str) -> Team | None:
        statement = select(Team).where(Team.id == team_id, Team.is_active.is_(True))
        return self.session.scalar(statement)

    def add(self, season: Season) -> None:
        self.session.add(season)

    def flush(self) -> None:
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def expire_all(self) -> None:
        self.session.expire_all()


def make_budget_transaction(
    *,
    season: Season,
    category,
    label: str,
    amount,
    reserve_applied,
    free_applied,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> BudgetTransaction:
    return BudgetTransaction(
        season_id=season.id,
        category=category,
        label=label,
        amount_millions=amount,
        reserve_applied_millions=reserve_applied,
        free_applied_millions=free_applied,
        reference_type=reference_type,
        reference_id=reference_id,
    )
