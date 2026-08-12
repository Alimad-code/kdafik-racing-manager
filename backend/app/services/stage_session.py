from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import status

from app.core.errors import DomainError, ErrorCode
from app.domain.enums import (
    BudgetCategory,
    CarCondition,
    PracticeCompletionStatus,
    PracticeSegment,
    PracticeSegmentStatus,
    SeasonStatus,
    SessionType,
    SetupBand,
    StageSessionStatus,
    StageSessionType,
    StageStatus,
)
from app.models import (
    Car,
    CarSetup,
    Season,
    SeasonStage,
    SessionResult,
    User,
)
from app.repositories.stage_session import StageSessionRepository
from app.schemas.season import BudgetTransactionRead, CarRead, PracticeProgramRead
from app.schemas.stage_session import (
    CarSetupRead,
    CarSetupSaveRequest,
    CarSetupSaveResponse,
    PracticeProgramResponse,
    PracticeResultRead,
    QualifyingResultRead,
    QualifyingRunResponse,
    RaceEventRead,
    RaceResultRead,
    RaceRunResponse,
)
from app.schemas.standings import (
    ConstructorStandingRead,
    DriverStandingRead,
    RepairCarResponse,
    StandingsRead,
)
from app.services.finance_pools import require_sufficient_funds, spend_budget
from app.services.live_simulation import LiveRaceEngine
from app.services.season import SeasonService
from app.services.simulation import (
    RaceSimulationResult,
    SimpleSimulationService,
)


class StageSessionService:
    def __init__(
        self,
        repository: StageSessionRepository,
        simulation: SimpleSimulationService | None = None,
    ) -> None:
        self.repository = repository
        self.simulation = simulation or SimpleSimulationService()

    def save_car_setups(
        self,
        season_id: UUID,
        stage_id: UUID,
        payload: CarSetupSaveRequest,
        user: User,
    ) -> CarSetupSaveResponse:
        try:
            season = self._get_owned_season_or_raise(season_id, user.id)
            stage = self._get_current_stage_or_raise(season, stage_id)
            self._validate_setup_target(stage, payload.applies_to_session)
            cars_by_id = self._cars_by_id(season)
            self._validate_unique_setup_cars(payload)

            total_setup_cost = Decimal("0.00")
            setup_cost_per_car = (
                season.selected_team.setup_cost_millions
                if season.selected_team
                else Decimal("0.00")
            )
            changes_to_apply = []

            for setup_input in payload.setups:
                car = cars_by_id.get(setup_input.car_id)
                if car is None:
                    raise DomainError(
                        ErrorCode.ENTITY_NOT_FOUND,
                        "Болид не принадлежит этому сезону.",
                        status_code=status.HTTP_404_NOT_FOUND,
                        details={"carId": str(setup_input.car_id)},
                    )

                if car.team_id != season.selected_team_id:
                    raise DomainError(
                        ErrorCode.INVALID_STATE_TRANSITION,
                        "Нельзя изменять настройки чужих болидов.",
                        details={"carId": str(car.id)},
                    )

                setup = self.repository.get_car_setup(
                    stage_id=stage.id,
                    car_id=car.id,
                    applies_to_session=payload.applies_to_session,
                )

                # Check if any setting changed
                is_changed = False
                if setup:
                    if (
                        setup.wings_setting != setup_input.wings_setting
                        or setup.suspension_setting != setup_input.suspension_setting
                        or setup.gearbox_setting != setup_input.gearbox_setting
                    ):
                        is_changed = True
                else:
                    if (
                        car.wings_setting != setup_input.wings_setting
                        or car.suspension_setting != setup_input.suspension_setting
                        or car.gearbox_setting != setup_input.gearbox_setting
                    ):
                        is_changed = True

                if is_changed:
                    total_setup_cost += setup_cost_per_car

                changes_to_apply.append((car, setup, setup_input, is_changed))

            require_sufficient_funds(
                season,
                total_setup_cost,
                "Недостаточно средств для настройки болидов.",
                category=BudgetCategory.SETUP,
            )

            for car, setup, setup_input, is_changed in changes_to_apply:
                if setup is None:
                    setup = CarSetup(
                        stage_id=stage.id,
                        car_id=car.id,
                        wings_setting=car.wings_setting,
                        suspension_setting=car.suspension_setting,
                        gearbox_setting=car.gearbox_setting,
                        setup_band=SetupBand.MEDIUM,
                        cost_millions=Decimal("0.00"),
                        applies_to_session=payload.applies_to_session,
                    )
                    self.repository.add(setup)

                if is_changed:
                    label = f"Setup change ({payload.applies_to_session.value}): {car.driver.code}"
                    spend_budget(
                        season=season,
                        category=BudgetCategory.SETUP,
                        label=label,
                        amount=setup_cost_per_car,
                        reference_type="car",
                        reference_id=str(car.id),
                        insufficient_funds_message="Недостаточно средств для настройки болида.",
                    )
                    setup.cost_millions += setup_cost_per_car

                setup.wings_setting = setup_input.wings_setting
                setup.suspension_setting = setup_input.suspension_setting
                setup.gearbox_setting = setup_input.gearbox_setting
                setup.setup_band = SetupBand.MEDIUM  # For now, simple band

                car.wings_setting = setup_input.wings_setting
                car.suspension_setting = setup_input.suspension_setting
                car.gearbox_setting = setup_input.gearbox_setting

            self.repository.flush()
            user_id = user.id
            self.repository.commit()
            self.repository.expire_all()
            return self._car_setup_response(
                season_id,
                user_id,
                stage_id,
                payload.applies_to_session,
            )
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def run_practice_segment(
        self,
        season_id: UUID,
        stage_id: UUID,
        segment: PracticeSegment,
        user: User,
    ) -> PracticeProgramResponse:
        try:
            season = self._get_owned_season_or_raise(season_id, user.id)
            stage = self._get_current_stage_or_raise(season, stage_id)

            # Validate state
            if segment == PracticeSegment.FP1:
                if stage.fp1_status == PracticeSegmentStatus.COMPLETED:
                    raise DomainError(
                        ErrorCode.SESSION_ALREADY_COMPLETED,
                        "FP1 уже завершена.",
                        status_code=status.HTTP_409_CONFLICT,
                    )
                if stage.fp1_status != PracticeSegmentStatus.AVAILABLE:
                    raise DomainError(ErrorCode.STAGE_LOCKED, "FP1 недоступна.")
            elif segment == PracticeSegment.FP2:
                if stage.fp2_status == PracticeSegmentStatus.COMPLETED:
                    raise DomainError(
                        ErrorCode.SESSION_ALREADY_COMPLETED,
                        "FP2 уже завершена.",
                        status_code=status.HTTP_409_CONFLICT,
                    )
                if stage.fp2_status != PracticeSegmentStatus.AVAILABLE:
                    raise DomainError(ErrorCode.PREVIOUS_SESSION_NOT_COMPLETED, "FP2 недоступна.")
            elif segment == PracticeSegment.FP3:
                if stage.fp3_status == PracticeSegmentStatus.COMPLETED:
                    raise DomainError(
                        ErrorCode.SESSION_ALREADY_COMPLETED,
                        "FP3 уже завершена.",
                        status_code=status.HTTP_409_CONFLICT,
                    )
                if stage.fp3_status != PracticeSegmentStatus.AVAILABLE:
                    raise DomainError(ErrorCode.PREVIOUS_SESSION_NOT_COMPLETED, "FP3 недоступна.")

            cars = self._session_cars(season)
            self._ensure_cars_ready_for_session(season, cars)
            self._ensure_default_setups(season, stage, cars, SessionType.PRACTICE)
            for result in self._build_practice_results(season, stage, cars, segment):
                self.repository.add(result)

            if segment == PracticeSegment.FP1:
                stage.fp1_status = PracticeSegmentStatus.COMPLETED
                stage.fp2_status = PracticeSegmentStatus.AVAILABLE
                stage.practice_completion_status = PracticeCompletionStatus.AVAILABLE
            elif segment == PracticeSegment.FP2:
                stage.fp2_status = PracticeSegmentStatus.COMPLETED
                stage.fp3_status = PracticeSegmentStatus.AVAILABLE
            elif segment == PracticeSegment.FP3:
                stage.fp3_status = PracticeSegmentStatus.COMPLETED

            user_id = user.id
            self.repository.commit()
            self.repository.expire_all()
            return self._practice_response(season_id, user_id, stage_id)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def complete_practice(
        self,
        season_id: UUID,
        stage_id: UUID,
        user: User,
    ) -> PracticeProgramResponse:
        try:
            season = self._get_owned_season_or_raise(season_id, user.id)
            stage = self._get_current_stage_or_raise(season, stage_id)

            if stage.practice_completion_status == PracticeCompletionStatus.COMPLETED:
                raise DomainError(
                    ErrorCode.SESSION_ALREADY_COMPLETED,
                    "Завершение практики уже выполнено.",
                    status_code=status.HTTP_409_CONFLICT,
                )

            has_completed_practice = any(
                stage.session_for_practice_segment(segment).status == StageSessionStatus.COMPLETED
                for segment in PracticeSegment
            )
            if (
                stage.practice_completion_status != PracticeCompletionStatus.AVAILABLE
                or not has_completed_practice
            ):
                raise DomainError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "Завершение практики недоступно. Нужно завершить хотя бы одну практику.",
                )

            cars = self._session_cars(season)
            self._ensure_cars_ready_for_session(season, cars)
            stage.practice_completion_status = PracticeCompletionStatus.COMPLETED
            for segment in (PracticeSegment.FP2, PracticeSegment.FP3):
                session = stage.session_for_practice_segment(segment)
                if session.status != StageSessionStatus.COMPLETED:
                    session.status = StageSessionStatus.LOCKED
            stage.practice_status = StageStatus.COMPLETED
            stage.qualifying_status = StageStatus.AVAILABLE

            user_id = user.id
            self.repository.commit()
            self.repository.expire_all()
            return self._practice_response(season_id, user_id, stage_id)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def run_qualifying(
        self,
        season_id: UUID,
        stage_id: UUID,
        user: User,
    ) -> QualifyingRunResponse:
        try:
            season = self._get_owned_season_or_raise(season_id, user.id)
            stage = self._get_current_stage_or_raise(season, stage_id)

            if stage.qualifying_status == StageStatus.COMPLETED:
                self._raise_completed_session(SessionType.QUALIFYING, stage)
            if stage.practice_status != StageStatus.COMPLETED:
                raise DomainError(
                    ErrorCode.PREVIOUS_SESSION_NOT_COMPLETED,
                    "Сначала нужно завершить практику.",
                    details={"stageId": str(stage.id)},
                )
            if stage.qualifying_status != StageStatus.AVAILABLE:
                raise DomainError(
                    ErrorCode.STAGE_LOCKED,
                    "Квалификация недоступна для этого этапа.",
                    details={"stageId": str(stage.id)},
                )

            cars = self._session_cars(season)
            self._ensure_cars_ready_for_session(season, cars)
            self._ensure_default_setups(season, stage, cars, SessionType.QUALIFYING)
            for result in self._build_qualifying_results(season, stage, cars):
                self.repository.add(result)

            stage.qualifying_status = StageStatus.COMPLETED
            stage.race_status = StageStatus.AVAILABLE

            user_id = user.id
            self.repository.commit()
            self.repository.expire_all()
            return self._qualifying_response(season_id, user_id, stage_id)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def persist_completed_live_race(
        self,
        season_id: UUID,
        stage_id: UUID,
        user_id: UUID,
        engine: LiveRaceEngine,
    ) -> RaceRunResponse:
        try:
            season = self._get_owned_season_or_raise(season_id, user_id)

            stage_for_replay = next(
                (item for item in season.stages if item.id == stage_id),
                None,
            )
            if stage_for_replay is None:
                raise DomainError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    "Этап не найден.",
                    status_code=status.HTTP_404_NOT_FOUND,
                    details={"stageId": str(stage_id)},
                )

            if stage_for_replay.race_status == StageStatus.COMPLETED:
                if self.repository.list_race_results(stage_for_replay.id):
                    return self._race_response(season_id, user_id, stage_for_replay.id)
                self._raise_completed_session(SessionType.RACE, stage_for_replay)

            stage = self._get_current_stage_or_raise(season, stage_id)

            if stage.race_status == StageStatus.COMPLETED:
                self._raise_completed_session(SessionType.RACE, stage)
            if stage.qualifying_status != StageStatus.COMPLETED:
                raise DomainError(
                    ErrorCode.PREVIOUS_SESSION_NOT_COMPLETED,
                    "Сначала нужно завершить квалификацию.",
                    details={"stageId": str(stage.id)},
                )
            if stage.race_status != StageStatus.AVAILABLE:
                raise DomainError(
                    ErrorCode.STAGE_LOCKED,
                    "Гонка недоступна для этого этапа.",
                    details={"stageId": str(stage.id)},
                )

            cars = self._session_cars(season)
            self._ensure_cars_ready_for_session(season, cars)
            self._ensure_default_setups(season, stage, cars, SessionType.RACE)

            cars_map = {str(car.id): car for car in season.cars}
            if not engine.is_complete():
                self._raise_live_not_finished(stage_id)
            race_simulation = engine.get_final_results(cars_map)
            if not race_simulation:
                raise DomainError(
                    ErrorCode.LIVE_RACE_NOT_FINISHED,
                    "Live-трансляция гонки еще не отдала итоговую классификацию.",
                    details={"stageId": str(stage_id)},
                )

            for result in self._build_race_results(season, stage, race_simulation):
                self.repository.add(result)

            stage.race_status = StageStatus.COMPLETED
            stage.status = StageStatus.COMPLETED
            next_stage = self._next_stage(season, stage)
            if next_stage is None:
                season.status = SeasonStatus.COMPLETED
                season.current_stage_id = None
                season.finished_at = datetime.now(UTC)
            else:
                next_stage.status = StageStatus.AVAILABLE
                next_stage.practice_status = StageStatus.AVAILABLE
                next_stage.fp1_status = PracticeSegmentStatus.AVAILABLE
                season.current_stage_id = next_stage.id
                for car in season.cars:
                    if car.team_id != season.selected_team_id:
                        car.condition = CarCondition.HEALTHY

            self.repository.commit()
            self.repository.expire_all()
            return self._race_response(season_id, user_id, stage_id)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def _raise_live_not_finished(self, stage_id: UUID) -> None:
        raise DomainError(
            ErrorCode.LIVE_RACE_NOT_FINISHED,
            "Live-трансляция гонки еще не завершена или недоступна.",
            details={"stageId": str(stage_id)},
        )

    def get_standings(self, season_id: UUID, user: User) -> StandingsRead:
        season = self._get_owned_season_or_raise(season_id, user.id)
        return self._standings_read(season)

    def get_practice_results(
        self,
        season_id: UUID,
        stage_id: UUID,
        user: User,
    ) -> PracticeProgramResponse:
        season, stage = self._get_stage_result_context_or_raise(season_id, stage_id, user.id)
        return self._practice_response(season.id, user.id, stage.id)

    def get_qualifying_results(
        self,
        season_id: UUID,
        stage_id: UUID,
        user: User,
    ) -> QualifyingRunResponse:
        season, stage = self._get_stage_result_context_or_raise(season_id, stage_id, user.id)
        results = self.repository.list_qualifying_results(stage.id)
        if not results:
            self._raise_missing_results(SessionType.QUALIFYING, stage)
        return self._qualifying_response(season.id, user.id, stage.id)

    def get_race_results(
        self,
        season_id: UUID,
        stage_id: UUID,
        user: User,
    ) -> RaceRunResponse:
        season, stage = self._get_stage_result_context_or_raise(season_id, stage_id, user.id)
        results = self.repository.list_race_results(stage.id)
        if not results:
            self._raise_missing_results(SessionType.RACE, stage)
        return self._race_response(season.id, user.id, stage.id)

    def get_car_setups(
        self,
        season_id: UUID,
        stage_id: UUID,
        session_type: SessionType,
        user: User,
    ) -> CarSetupSaveResponse:
        season, stage = self._get_stage_result_context_or_raise(season_id, stage_id, user.id)
        return self._car_setup_response(season.id, user.id, stage.id, session_type)

    def repair_car(
        self,
        season_id: UUID,
        car_id: UUID,
        user: User,
    ) -> RepairCarResponse:
        try:
            season = self._get_owned_season_or_raise(season_id, user.id)
            if season.status == SeasonStatus.COMPLETED:
                raise DomainError(
                    ErrorCode.SEASON_ALREADY_FINISHED,
                    "Сезон уже завершен.",
                    status_code=status.HTTP_409_CONFLICT,
                    details={"seasonId": str(season.id)},
                )
            car = next((item for item in season.cars if item.id == car_id), None)
            if car is None:
                raise DomainError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    "Болид не найден.",
                    status_code=status.HTTP_404_NOT_FOUND,
                    details={"carId": str(car_id)},
                )
            if car.condition == CarCondition.HEALTHY:
                raise DomainError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "Болид уже исправен.",
                    status_code=status.HTTP_409_CONFLICT,
                    details={"carId": str(car.id)},
                )

            amount = self._repair_cost(car)
            transaction = spend_budget(
                season=season,
                category=BudgetCategory.REPAIR,
                label=f"Repair car: {car.driver.code}",
                amount=amount,
                reference_type="car",
                reference_id=str(car.id),
                insufficient_funds_message="Недостаточно средств для ремонта болида.",
            )
            if transaction is None:
                raise RuntimeError("Car repair must create a budget transaction.")
            car.condition = CarCondition.HEALTHY

            self.repository.flush()
            user_id = user.id
            transaction_id = transaction.id
            self.repository.commit()
            self.repository.expire_all()
            return self._repair_response(season_id, user_id, car_id, transaction_id)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def _get_owned_season_or_raise(self, season_id: UUID, user_id: UUID) -> Season:
        season = self.repository.get_for_user(season_id, user_id)
        if season is None:
            raise DomainError(
                ErrorCode.ENTITY_NOT_FOUND,
                "Сезон не найден.",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"seasonId": str(season_id)},
            )
        return season

    def _get_car_or_raise(self, season: Season, car_id: UUID) -> Car:
        car = next((item for item in season.cars if item.id == car_id), None)
        if car is None:
            raise DomainError(
                ErrorCode.ENTITY_NOT_FOUND,
                "Болид не найден.",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"carId": str(car_id)},
            )
        return car

    def _get_current_stage_or_raise(self, season: Season, stage_id: UUID) -> SeasonStage:
        if season.status == SeasonStatus.SETUP:
            raise DomainError(
                ErrorCode.SEASON_NOT_IN_PROGRESS,
                "Сезон должен быть начат перед запуском сессий.",
                details={"seasonId": str(season.id)},
            )
        if season.status == SeasonStatus.COMPLETED:
            raise DomainError(
                ErrorCode.SEASON_ALREADY_FINISHED,
                "Сезон уже завершен.",
                status_code=status.HTTP_409_CONFLICT,
                details={"seasonId": str(season.id)},
            )

        stage = next((item for item in season.stages if item.id == stage_id), None)
        if stage is None:
            raise DomainError(
                ErrorCode.ENTITY_NOT_FOUND,
                "Этап не найден.",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"stageId": str(stage_id)},
            )
        if stage.status == StageStatus.COMPLETED:
            raise DomainError(
                ErrorCode.SESSION_ALREADY_COMPLETED,
                "Этап уже завершен.",
                status_code=status.HTTP_409_CONFLICT,
                details={"stageId": str(stage.id)},
            )
        if stage.id != season.current_stage_id or stage.status != StageStatus.AVAILABLE:
            raise DomainError(
                ErrorCode.STAGE_LOCKED,
                "Этап заблокирован или не является текущим.",
                details={
                    "stageId": str(stage.id),
                    "currentStageId": str(season.current_stage_id)
                    if season.current_stage_id is not None
                    else None,
                },
            )
        return stage

    def _get_stage_result_context_or_raise(
        self,
        season_id: UUID,
        stage_id: UUID,
        user_id: UUID,
    ) -> tuple[Season, SeasonStage]:
        season = self._get_owned_season_or_raise(season_id, user_id)
        stage = next((item for item in season.stages if item.id == stage_id), None)
        if stage is None:
            raise DomainError(
                ErrorCode.ENTITY_NOT_FOUND,
                "Этап не найден.",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"stageId": str(stage_id)},
            )
        return season, stage

    def _validate_setup_target(self, stage: SeasonStage, session_type: SessionType) -> None:
        session_status = self._session_status(stage, session_type)
        if session_status == StageStatus.COMPLETED:
            self._raise_completed_session(session_type, stage)
        if session_status == StageStatus.LOCKED:
            raise DomainError(
                ErrorCode.PREVIOUS_SESSION_NOT_COMPLETED,
                "Сначала нужно завершить предыдущую сессию.",
                details={"stageId": str(stage.id), "session": session_type.value},
            )

    def _session_status(self, stage: SeasonStage, session_type: SessionType) -> StageStatus:
        if session_type == SessionType.PRACTICE:
            return stage.practice_status
        if session_type == SessionType.QUALIFYING:
            return stage.qualifying_status
        return stage.race_status

    def _validate_unique_setup_cars(self, payload: CarSetupSaveRequest) -> None:
        car_ids = [setup.car_id for setup in payload.setups]
        if len(car_ids) != len(set(car_ids)):
            raise DomainError(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Запрос настроек содержит повторяющиеся болиды.",
                details={"carIds": [str(car_id) for car_id in car_ids]},
            )

    def _cars_by_id(self, season: Season) -> dict[UUID, Car]:
        return {car.id: car for car in season.cars}

    def _session_cars(self, season: Season) -> list[Car]:
        cars = sorted(season.cars, key=lambda item: item.driver_id)
        player_cars = [car for car in cars if car.team_id == season.selected_team_id]
        if len(player_cars) != 2:
            raise DomainError(
                ErrorCode.INVALID_ROSTER,
                "У игрока должно быть ровно два болида.",
                details={"carCount": len(player_cars)},
            )
        return cars

    def _ensure_cars_ready_for_session(self, season: Season, cars: list[Car]) -> None:
        blocked_cars = [
            car
            for car in cars
            if car.team_id == season.selected_team_id
            and car.condition == CarCondition.HEAVILY_DAMAGED
        ]
        if not blocked_cars:
            return
        raise DomainError(
            ErrorCode.INVALID_STATE_TRANSITION,
            "Сильно повреждённый болид нужно отремонтировать перед следующей сессией.",
            status_code=status.HTTP_409_CONFLICT,
            details={"carIds": [str(car.id) for car in blocked_cars]},
        )

    def _ensure_default_setups(
        self,
        season: Season,
        stage: SeasonStage,
        cars: list[Car],
        session_type: SessionType,
    ) -> None:
        for car in cars:
            setup = self.repository.get_car_setup(
                stage_id=stage.id,
                car_id=car.id,
                applies_to_session=session_type,
            )
            if setup is None:
                self.repository.add(
                    CarSetup(
                        stage_id=stage.id,
                        car_id=car.id,
                        wings_setting=car.wings_setting,
                        suspension_setting=car.suspension_setting,
                        gearbox_setting=car.gearbox_setting,
                        setup_band=SetupBand.MEDIUM,
                        cost_millions=Decimal("0.00"),
                        applies_to_session=session_type,
                    )
                )
        self.repository.flush()

    def _setup_map(self, stage_id: UUID, session_type: SessionType) -> dict[UUID, CarSetup]:
        return {
            setup.car_id: setup for setup in self.repository.list_car_setups(stage_id, session_type)
        }

    def _build_practice_results(
        self,
        season: Season,
        stage: SeasonStage,
        cars: list[Car],
        segment: PracticeSegment,
    ) -> list[SessionResult]:
        simulated_results = self.simulation.simulate_practice(
            stage,
            cars,
            self._setup_map(stage.id, SessionType.PRACTICE),
            segment,
        )
        stage_session = stage.session_for_practice_segment(segment)
        return [
            SessionResult(
                stage_session=stage_session,
                car_id=result.car.id,
                position=result.position,
                grid_position=None,
                best_lap=result.best_lap,
                best_lap_number=None,
                max_speed_kph=None,
                gap=result.gap,
                laps=result.laps,
                points=0,
                status=result.status,
                event=result.event,
                reason=result.reason,
                setup_feedback=result.setup_feedback,
                engineer_recommendation=result.engineer_recommendation,
                event_description=None,
                event_severity=None,
            )
            for result in simulated_results
        ]

    def _build_qualifying_results(
        self,
        season: Season,
        stage: SeasonStage,
        cars: list[Car],
    ) -> list[SessionResult]:
        simulated_results = self.simulation.simulate_qualifying(
            stage,
            cars,
            self._setup_map(stage.id, SessionType.QUALIFYING),
        )
        stage_session = stage.session_for(StageSessionType.QUALIFYING)
        return [
            SessionResult(
                stage_session=stage_session,
                car_id=result.car.id,
                position=result.position,
                grid_position=None,
                best_lap=result.best_lap,
                best_lap_number=None,
                max_speed_kph=None,
                gap=result.gap,
                laps=result.laps,
                points=0,
                status=result.status,
                event=result.event,
                reason=result.reason,
                setup_feedback=None,
                engineer_recommendation=None,
                event_description=None,
                event_severity=None,
            )
            for result in simulated_results
        ]

    def _simulate_race(
        self,
        stage: SeasonStage,
        cars: list[Car],
    ) -> list[RaceSimulationResult]:
        return self.simulation.simulate_race(
            stage,
            cars,
            self._setup_map(stage.id, SessionType.RACE),
            self.repository.list_qualifying_results(stage.id),
        )

    def _build_race_results(
        self,
        season: Season,
        stage: SeasonStage,
        simulated_results: list[RaceSimulationResult],
    ) -> list[SessionResult]:
        for result in simulated_results:
            if result.resulting_condition is not None:
                result.car.condition = result.resulting_condition

        stage_session = stage.session_for(StageSessionType.RACE)
        return [
            SessionResult(
                stage_session=stage_session,
                car_id=result.car.id,
                position=result.finish_position,
                grid_position=result.grid_position,
                best_lap=result.best_lap,
                best_lap_number=result.best_lap_number,
                max_speed_kph=result.max_speed_kph,
                gap=result.gap,
                laps=result.laps,
                points=result.points,
                status=result.status,
                event=result.event,
                reason=result.reason,
                setup_feedback=None,
                engineer_recommendation=None,
                event_description=result.event_description,
                event_severity=result.event_severity,
            )
            for result in simulated_results
        ]

    def _repair_cost(self, car: Car) -> Decimal:
        if car.condition == CarCondition.HEAVILY_DAMAGED:
            return car.team.repair_cost_millions * Decimal("2")
        return car.team.repair_cost_millions

    def _next_stage(self, season: Season, stage: SeasonStage) -> SeasonStage | None:
        return next(
            (item for item in season.stages if item.stage_number == stage.stage_number + 1),
            None,
        )

    def _raise_completed_session(self, session_type: SessionType, stage: SeasonStage) -> None:
        raise DomainError(
            ErrorCode.SESSION_ALREADY_COMPLETED,
            "Сессия уже завершена.",
            status_code=status.HTTP_409_CONFLICT,
            details={"stageId": str(stage.id), "session": session_type.value},
        )

    def _raise_missing_results(self, session_type: SessionType, stage: SeasonStage) -> None:
        raise DomainError(
            ErrorCode.ENTITY_NOT_FOUND,
            "Результаты сессии еще не сохранены.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"stageId": str(stage.id), "session": session_type.value},
        )

    def _car_setup_response(
        self,
        season_id: UUID,
        user_id: UUID,
        stage_id: UUID,
        session_type: SessionType,
    ) -> CarSetupSaveResponse:
        season, stage = self._response_context(season_id, user_id, stage_id)
        return CarSetupSaveResponse(
            season=SeasonService.to_read(season),
            stage=self._stage_read(season, stage),
            setups=[
                CarSetupRead.model_validate(setup)
                for setup in self.repository.list_car_setups(stage_id, session_type)
            ],
        )

    def _practice_response(
        self,
        season_id: UUID,
        user_id: UUID,
        stage_id: UUID,
    ) -> PracticeProgramResponse:
        season, stage = self._response_context(season_id, user_id, stage_id)
        return PracticeProgramResponse(
            season=SeasonService.to_read(season),
            stage=self._stage_read(season, stage),
            practice_program=PracticeProgramRead(
                stage_id=stage.id,
                fp1_status=stage.fp1_status,
                fp2_status=stage.fp2_status,
                fp3_status=stage.fp3_status,
                practice_completion_status=stage.practice_completion_status,
            ),
            practice_results=[
                PracticeResultRead.model_validate(result)
                for result in self.repository.list_practice_results(stage_id)
            ],
        )

    def _qualifying_response(
        self,
        season_id: UUID,
        user_id: UUID,
        stage_id: UUID,
    ) -> QualifyingRunResponse:
        season, stage = self._response_context(season_id, user_id, stage_id)
        return QualifyingRunResponse(
            season=SeasonService.to_read(season),
            stage=self._stage_read(season, stage),
            qualifying_results=[
                QualifyingResultRead.model_validate(result)
                for result in self.repository.list_qualifying_results(stage_id)
            ],
        )

    def _race_response(self, season_id: UUID, user_id: UUID, stage_id: UUID) -> RaceRunResponse:
        season, stage = self._response_context(season_id, user_id, stage_id)
        return RaceRunResponse(
            season=SeasonService.to_read(season),
            stage=self._stage_read(season, stage),
            race_results=[
                RaceResultRead.model_validate(result)
                for result in self.repository.list_race_results(stage_id)
            ],
            events=[
                RaceEventRead.model_validate(event)
                for event in self.repository.list_race_events(stage_id)
            ],
            standings=self._standings_read(season),
        )

    def _repair_response(
        self,
        season_id: UUID,
        user_id: UUID,
        car_id: UUID,
        transaction_id: UUID,
    ) -> RepairCarResponse:
        season = self._get_owned_season_or_raise(season_id, user_id)
        car = next(item for item in season.cars if item.id == car_id)
        transaction = next(item for item in season.budget_transactions if item.id == transaction_id)
        return RepairCarResponse(
            season=SeasonService.to_read(season),
            car=CarRead.model_validate(car),
            transaction=BudgetTransactionRead.model_validate(transaction),
        )

    def _standings_read(self, season: Season) -> StandingsRead:
        race_results = [
            result
            for stage in season.stages
            for session in stage.sessions
            if session.type == StageSessionType.RACE
            for result in session.results
        ]
        if not race_results:
            return StandingsRead(
                driver_standings=[],
                constructor_standings=[],
                selected_team_rank=None,
            )

        driver_standings_by_id = {
            car.driver_id: SimpleNamespace(
                id=uuid5(NAMESPACE_URL, f"{season.id}:driver:{car.driver_id}"),
                season_id=season.id,
                driver_id=car.driver_id,
                team_id=car.team_id,
                position=0,
                points=0,
                wins=0,
                podiums=0,
                driver=car.driver,
                team=car.team,
            )
            for car in season.cars
        }
        constructor_standings_by_id = {
            car.team_id: SimpleNamespace(
                id=uuid5(NAMESPACE_URL, f"{season.id}:constructor:{car.team_id}"),
                season_id=season.id,
                team_id=car.team_id,
                position=0,
                points=0,
                wins=0,
                podiums=0,
                team=car.team,
            )
            for car in season.cars
        }
        for result in race_results:
            driver_standing = driver_standings_by_id[result.car.driver_id]
            constructor_standing = constructor_standings_by_id[result.car.team_id]
            driver_standing.points += result.points
            constructor_standing.points += result.points
            if result.position == 1 and result.points > 0:
                driver_standing.wins += 1
                constructor_standing.wins += 1
            if result.position <= 3 and result.points > 0:
                driver_standing.podiums += 1
                constructor_standing.podiums += 1

        driver_standings = sorted(
            driver_standings_by_id.values(),
            key=lambda item: (-item.points, -item.wins, -item.podiums, item.driver_id),
        )
        constructor_standings = sorted(
            constructor_standings_by_id.values(),
            key=lambda item: (-item.points, -item.wins, -item.podiums, item.team_id),
        )
        for position, standing in enumerate(driver_standings, start=1):
            standing.position = position
        for position, standing in enumerate(constructor_standings, start=1):
            standing.position = position

        selected_team_rank = next(
            (
                standing.position
                for standing in constructor_standings
                if standing.team_id == season.selected_team_id
            ),
            None,
        )
        return StandingsRead(
            driver_standings=[
                DriverStandingRead.model_validate(standing) for standing in driver_standings
            ],
            constructor_standings=[
                ConstructorStandingRead.model_validate(standing)
                for standing in constructor_standings
            ],
            selected_team_rank=selected_team_rank,
        )

    def _response_context(
        self,
        season_id: UUID,
        user_id: UUID,
        stage_id: UUID,
    ) -> tuple[Season, SeasonStage]:
        season = self._get_owned_season_or_raise(season_id, user_id)
        stage = next(item for item in season.stages if item.id == stage_id)
        return season, stage

    def _stage_read(self, season: Season, stage: SeasonStage):
        season_read = SeasonService.to_read(season)
        return next(item for item in season_read.stages if item.id == stage.id)
