from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import SessionType, StageSessionType
from app.models import (
    Car,
    CarSetup,
    Season,
    SeasonStage,
    SessionResult,
    StageSession,
    Track,
)


class StageSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_for_user(self, season_id: UUID, user_id: UUID) -> Season | None:
        statement = (
            select(Season)
            .where(Season.id == season_id, Season.user_id == user_id)
            .options(
                selectinload(Season.selected_team),
                selectinload(Season.stages)
                .selectinload(SeasonStage.track)
                .selectinload(Track.segments),
                selectinload(Season.stages).selectinload(SeasonStage.sessions),
                selectinload(Season.stages)
                .selectinload(SeasonStage.sessions)
                .selectinload(StageSession.results)
                .selectinload(SessionResult.car)
                .selectinload(Car.driver),
                selectinload(Season.stages)
                .selectinload(SeasonStage.sessions)
                .selectinload(StageSession.results)
                .selectinload(SessionResult.car)
                .selectinload(Car.team),
                selectinload(Season.cars).selectinload(Car.driver),
                selectinload(Season.cars).selectinload(Car.team),
                selectinload(Season.budget_transactions),
            )
        )
        return self.session.scalar(statement)

    def get_car_setup(
        self,
        *,
        stage_id: UUID,
        car_id: UUID,
        applies_to_session: SessionType,
    ) -> CarSetup | None:
        statement = select(CarSetup).where(
            CarSetup.stage_id == stage_id,
            CarSetup.car_id == car_id,
            CarSetup.applies_to_session == applies_to_session,
        )
        return self.session.scalar(statement)

    def list_car_setups(self, stage_id: UUID, applies_to_session: SessionType) -> list[CarSetup]:
        statement = (
            select(CarSetup)
            .where(
                CarSetup.stage_id == stage_id,
                CarSetup.applies_to_session == applies_to_session,
            )
            .options(selectinload(CarSetup.stage))
            .order_by(CarSetup.car_id)
        )
        return list(self.session.scalars(statement))

    def list_practice_results(self, stage_id: UUID) -> list[SessionResult]:
        statement = (
            select(SessionResult)
            .join(SessionResult.stage_session)
            .where(
                StageSession.stage_id == stage_id,
                StageSession.type.in_(
                    [StageSessionType.FP1, StageSessionType.FP2, StageSessionType.FP3]
                ),
            )
            .options(
                selectinload(SessionResult.car).selectinload(Car.team),
                selectinload(SessionResult.stage_session).selectinload(StageSession.stage),
            )
            .order_by(SessionResult.position)
        )
        return list(self.session.scalars(statement))

    def list_qualifying_results(self, stage_id: UUID) -> list[SessionResult]:
        statement = (
            select(SessionResult)
            .join(SessionResult.stage_session)
            .where(
                StageSession.stage_id == stage_id,
                StageSession.type == StageSessionType.QUALIFYING,
            )
            .options(
                selectinload(SessionResult.car).selectinload(Car.team),
                selectinload(SessionResult.stage_session).selectinload(StageSession.stage),
            )
            .order_by(SessionResult.position)
        )
        return list(self.session.scalars(statement))

    def list_race_results(self, stage_id: UUID) -> list[SessionResult]:
        statement = (
            select(SessionResult)
            .join(SessionResult.stage_session)
            .where(
                StageSession.stage_id == stage_id,
                StageSession.type == StageSessionType.RACE,
            )
            .options(
                selectinload(SessionResult.car).selectinload(Car.team),
                selectinload(SessionResult.stage_session).selectinload(StageSession.stage),
            )
            .order_by(SessionResult.position)
        )
        return list(self.session.scalars(statement))

    def list_race_events(self, stage_id: UUID) -> list[SessionResult]:
        return [result for result in self.list_race_results(stage_id) if result.event is not None]

    def add(self, instance: object) -> None:
        self.session.add(instance)

    def flush(self) -> None:
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def expire_all(self) -> None:
        self.session.expire_all()
