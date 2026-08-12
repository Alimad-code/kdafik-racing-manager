from __future__ import annotations

import random
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import status

from app.core.errors import DomainError, ErrorCode
from app.domain.constants import STARTING_BUDGET_MILLIONS
from app.domain.enums import (
    BudgetCategory,
    CarCondition,
    PracticeSegmentStatus,
    SeasonStatus,
    SessionType,
    StageSessionStatus,
    StageSessionType,
    StageStatus,
)
from app.models import Car, Driver, Season, SeasonStage, StageSession, Team, User
from app.repositories.season import SeasonRepository
from app.schemas.catalog import DriverRead, TeamRead, TrackRead
from app.schemas.season import (
    BudgetStateRead,
    BudgetTransactionRead,
    CarRead,
    PracticeProgramRead,
    SeasonCreate,
    SeasonRead,
    SeasonStageRead,
    SeasonSummaryRead,
    TireStrategyRead,
    TireStrategyStintRead,
)
from app.seed import MVP_CALENDAR
from app.services.finance_pools import free_budget, spend_budget
from app.services.tire_strategy import build_tire_strategies, recommended_starting_compound
from app.services.weather import (
    build_weather_payload,
    climate_from_track,
    create_weather_scenario,
    stable_weather_seed,
)

BUDGET_TRANSACTION_ORDER = {
    BudgetCategory.DRIVERS: 0,
    BudgetCategory.TEAM: 1,
    BudgetCategory.CAR_CONSTRUCTION: 2,
    BudgetCategory.SETUP: 3,
    BudgetCategory.REPAIR: 4,
}


class SeasonService:
    def __init__(self, repository: SeasonRepository) -> None:
        self.repository = repository

    def create_season(self, payload: SeasonCreate, user: User) -> SeasonRead:
        try:
            season = self._create_initial_season(payload, user)
            user.active_season_id = season.id
            self.repository.commit()
            self.repository.expire_all()
            return self._get_read_for_user_or_raise(season.id, user.id)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def create_initial_season_model(self, payload: SeasonCreate, user: User) -> Season:
        return self._create_initial_season(payload, user)

    def get_season(self, season_id: UUID, user: User) -> SeasonRead:
        return self._get_read_for_user_or_raise(season_id, user.id)

    def list_seasons(self, user: User) -> list[SeasonSummaryRead]:
        seasons = self.repository.list_for_user(user.id)
        return [self._to_summary_read(season) for season in seasons]

    def get_budget_transactions(self, season_id: UUID, user: User) -> list[BudgetTransactionRead]:
        season = self.repository.get_for_user(season_id, user.id)
        if season is None:
            raise DomainError(
                ErrorCode.ENTITY_NOT_FOUND,
                "Сезон не найден.",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"seasonId": str(season_id)},
            )
        return [
            BudgetTransactionRead.model_validate(transaction)
            for transaction in sorted(
                season.budget_transactions, key=lambda item: item.created_at, reverse=True
            )
        ]

    def restart_season(self, season_id: UUID, user: User) -> SeasonRead:
        try:
            season = self.repository.get_for_user(season_id, user.id)
            if season is None:
                raise DomainError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    "Сезон не найден.",
                    status_code=status.HTTP_404_NOT_FOUND,
                    details={"seasonId": str(season_id)},
                )

            if not self._is_restartable(season):
                raise DomainError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "Новый сезон можно начать только после завершения текущего сезона.",
                    status_code=status.HTTP_409_CONFLICT,
                    details={"seasonId": str(season_id), "status": season.status.value},
                )

            new_season = self._create_initial_season(SeasonCreate(), user)
            user.active_season_id = new_season.id
            self.repository.commit()
            self.repository.expire_all()
            return self._get_read_for_user_or_raise(new_season.id, user.id)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def confirm_roster(
        self,
        season_id: UUID,
        driver_ids: list[str],
        team_id: str,
        user: User,
    ) -> SeasonRead:
        try:
            season = self.repository.get_for_user(season_id, user.id)
            if season is None:
                raise DomainError(
                    ErrorCode.ENTITY_NOT_FOUND,
                    "Сезон не найден.",
                    status_code=status.HTTP_404_NOT_FOUND,
                    details={"seasonId": str(season_id)},
                )

            if season.status != SeasonStatus.SETUP:
                raise DomainError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "Состав можно подтвердить только для сезона в статусе setup.",
                    status_code=status.HTTP_409_CONFLICT,
                    details={"status": season.status.value},
                )

            drivers = self._validate_driver_selection(driver_ids)
            team = self._validate_team_selection(team_id)
            roster_cost = self._calculate_roster_cost(drivers, team)
            repair_reserve = team.minimum_repair_reserve_millions
            setup_reserve = team.minimum_setup_reserve_millions
            required_total = roster_cost + repair_reserve + setup_reserve
            if season.available_budget_millions < required_total:
                raise DomainError(
                    ErrorCode.INSUFFICIENT_FUNDS,
                    "Недостаточно средств для подтверждения состава.",
                    details={
                        "rosterCost": float(roster_cost),
                        "repairReserve": float(repair_reserve),
                        "setupReserve": float(setup_reserve),
                        "requiredTotal": float(required_total),
                        "available": float(season.available_budget_millions),
                    },
                )

            self._apply_roster_confirmation(season, drivers, team)
            season.status = SeasonStatus.IN_PROGRESS
            season.selected_team_id = team.id
            first_stage = self._get_first_stage(season)
            first_stage.status = StageStatus.AVAILABLE
            first_stage.practice_status = StageStatus.AVAILABLE
            first_stage.fp1_status = PracticeSegmentStatus.AVAILABLE
            season.current_stage_id = first_stage.id
            user.active_season_id = season.id

            self.repository.commit()
            self.repository.expire_all()
            return self._get_read_for_user_or_raise(season.id, user.id)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def _apply_roster_confirmation(
        self,
        season: Season,
        drivers: list[Driver],
        team: Team,
    ) -> None:
        # Create player's team
        next_slot = 1
        for slot, driver in enumerate(drivers, start=1):
            season.cars.append(
                Car(
                    team=team,
                    driver=driver,
                    slot=slot,
                    is_player=True,
                    driver_first_name_snapshot=driver.first_name,
                    driver_last_name_snapshot=driver.last_name,
                    driver_code_snapshot=driver.code,
                    team_name_snapshot=team.name,
                    team_short_name_snapshot=team.short_name,
                    team_color_snapshot=team.color,
                    engine_power=team.engine_power,
                    aero_efficiency=team.aero_efficiency,
                    chassis_grip=team.chassis_grip,
                    reliability=team.reliability,
                    condition=CarCondition.HEALTHY,
                    wings_setting=50,
                    suspension_setting=50,
                    gearbox_setting=50,
                )
            )
            next_slot = slot + 1

        # Create AI teams
        all_drivers = self.repository.list_active_drivers()
        all_teams = self.repository.list_active_teams()

        selected_driver_ids = {driver.id for driver in drivers}
        remaining_drivers = [d for d in all_drivers if d.id not in selected_driver_ids]
        remaining_teams = [t for t in all_teams if t.id != team.id]

        random.shuffle(remaining_drivers)

        for ai_team in remaining_teams:
            if len(remaining_drivers) < 2:
                break
            for _ in range(2):
                ai_driver = remaining_drivers.pop()
                season.cars.append(
                    Car(
                        team=ai_team,
                        driver=ai_driver,
                        slot=next_slot,
                        is_player=False,
                        driver_first_name_snapshot=ai_driver.first_name,
                        driver_last_name_snapshot=ai_driver.last_name,
                        driver_code_snapshot=ai_driver.code,
                        team_name_snapshot=ai_team.name,
                        team_short_name_snapshot=ai_team.short_name,
                        team_color_snapshot=ai_team.color,
                        engine_power=ai_team.engine_power,
                        aero_efficiency=ai_team.aero_efficiency,
                        chassis_grip=ai_team.chassis_grip,
                        reliability=ai_team.reliability,
                        condition=CarCondition.HEALTHY,
                        wings_setting=50,
                        suspension_setting=50,
                        gearbox_setting=50,
                    )
                )
                next_slot += 1

        driver_cost = sum((driver.price_millions for driver in drivers), Decimal("0.00"))
        spend_budget(
            season,
            category=BudgetCategory.DRIVERS,
            label="Drivers roster confirmation",
            amount=driver_cost,
            reference_type="drivers",
            reference_id=",".join(driver.id for driver in drivers),
        )
        spend_budget(
            season,
            category=BudgetCategory.TEAM,
            label=f"Team entry: {team.name}",
            amount=team.price_millions,
            reference_type="team",
            reference_id=team.id,
        )
        spend_budget(
            season,
            category=BudgetCategory.CAR_CONSTRUCTION,
            label="Construct 2 cars",
            amount=team.car_build_cost_millions * Decimal("2"),
            reference_type="team",
            reference_id=team.id,
        )
        season.repair_reserve_millions = team.minimum_repair_reserve_millions
        season.setup_reserve_millions = team.minimum_setup_reserve_millions

    def _validate_driver_selection(self, driver_ids: list[str]) -> list[Driver]:
        if len(driver_ids) != 2:
            raise DomainError(
                ErrorCode.INVALID_ROSTER,
                "Нужно выбрать ровно двух пилотов.",
                details={"driverIds": driver_ids},
            )
        if len(set(driver_ids)) != 2:
            raise DomainError(
                ErrorCode.DUPLICATE_DRIVER,
                "Нельзя выбрать одного пилота дважды.",
                details={"driverIds": driver_ids},
            )

        drivers = self.repository.list_active_drivers_by_ids(driver_ids)
        drivers_by_id = {driver.id: driver for driver in drivers}
        missing_ids = [driver_id for driver_id in driver_ids if driver_id not in drivers_by_id]
        if missing_ids:
            raise DomainError(
                ErrorCode.INVALID_ROSTER,
                "Один или несколько пилотов недоступны для выбора.",
                details={"missingDriverIds": missing_ids},
            )
        return [drivers_by_id[driver_id] for driver_id in driver_ids]

    def _validate_team_selection(self, team_id: str) -> Team:
        team = self.repository.get_active_team(team_id)
        if team is None:
            raise DomainError(
                ErrorCode.INVALID_ROSTER,
                "Команда недоступна для выбора.",
                details={"teamId": team_id},
            )
        return team

    def _calculate_roster_cost(self, drivers: list[Driver], team: Team) -> Decimal:
        driver_cost = sum((driver.price_millions for driver in drivers), Decimal("0.00"))
        return driver_cost + team.price_millions + team.car_build_cost_millions * Decimal("2")

    def _validate_mvp_tracks_exist(self) -> None:
        track_ids = {stage["track_id"] for stage in MVP_CALENDAR}
        tracks = self.repository.list_tracks_by_ids(track_ids)
        found_ids = {track.id for track in tracks}
        missing_ids = sorted(track_ids - found_ids)
        if missing_ids:
            raise DomainError(
                ErrorCode.ENTITY_NOT_FOUND,
                "Не найдены трассы календаря MVP.",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"trackIds": missing_ids},
            )

    def _create_initial_season(self, payload: SeasonCreate, user: User) -> Season:
        self._validate_mvp_tracks_exist()
        season_id = uuid4()
        tracks_by_id = {
            track.id: track
            for track in self.repository.list_tracks_by_ids(
                {stage["track_id"] for stage in MVP_CALENDAR}
            )
        }
        season = Season(
            id=season_id,
            user_id=user.id,
            name=payload.name,
            year=payload.year,
            status=SeasonStatus.SETUP,
            starting_budget_millions=STARTING_BUDGET_MILLIONS,
            initial_repair_reserve_millions=Decimal("0.00"),
            initial_setup_reserve_millions=Decimal("0.00"),
        )
        for calendar_stage in MVP_CALENDAR:
            stage_id = uuid4()
            track = tracks_by_id[calendar_stage["track_id"]]
            season.stages.append(
                SeasonStage(
                    id=stage_id,
                    track_id=calendar_stage["track_id"],
                    stage_number=calendar_stage["stage_number"],
                    weekend_date=calendar_stage["weekend_date"],
                    weather_scenario=create_weather_scenario(
                        seed=stable_weather_seed(season_id, stage_id),
                        climate=climate_from_track(track),
                    ),
                    sessions=[
                        StageSession(
                            type=session_type,
                            status=StageSessionStatus.LOCKED,
                            sort_order=index,
                        )
                        for index, session_type in enumerate(
                            (
                                StageSessionType.FP1,
                                StageSessionType.FP2,
                                StageSessionType.FP3,
                                StageSessionType.PRACTICE_COMPLETION,
                                StageSessionType.QUALIFYING,
                                StageSessionType.RACE,
                            ),
                            start=1,
                        )
                    ],
                )
            )

        self.repository.add(season)
        self.repository.flush()
        return season

    @staticmethod
    def _is_restartable(season: Season) -> bool:
        return True

    def _get_first_stage(self, season: Season) -> SeasonStage:
        for stage in sorted(season.stages, key=lambda item: item.stage_number):
            if stage.stage_number == 1:
                return stage
        raise DomainError(
            ErrorCode.INVALID_STATE_TRANSITION,
            "У сезона нет первого этапа.",
            status_code=status.HTTP_409_CONFLICT,
        )

    def _get_read_for_user_or_raise(self, season_id: UUID, user_id: UUID) -> SeasonRead:
        season = self.repository.get_for_user(season_id, user_id)
        if season is None:
            raise DomainError(
                ErrorCode.ENTITY_NOT_FOUND,
                "Сезон не найден.",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"seasonId": str(season_id)},
            )
        return self._to_read(season)

    @staticmethod
    def to_read(season: Season) -> SeasonRead:
        stage_reads = [
            SeasonService._stage_to_read(stage)
            for stage in sorted(season.stages, key=lambda item: item.stage_number)
        ]
        return SeasonRead(
            id=season.id,
            user_id=season.user_id,
            name=season.name,
            year=season.year,
            status=season.status,
            selected_team_id=season.selected_team_id,
            current_stage_id=season.current_stage_id,
            current_stage=next(
                (stage for stage in stage_reads if stage.id == season.current_stage_id),
                None,
            ),
            budget=SeasonService._budget_to_read(season),
            selected_drivers=[
                DriverRead.model_validate(driver) for driver in season.selected_drivers
            ],
            selected_team=TeamRead.model_validate(season.selected_team)
            if season.selected_team is not None
            else None,
            cars=[
                CarRead.model_validate(car)
                for car in sorted(season.cars, key=lambda item: item.slot)
                if car.is_player
            ]
            if season.selected_team_id
            else [],
            stages=stage_reads,
            budget_transactions=[
                BudgetTransactionRead.model_validate(transaction)
                for transaction in sorted(
                    season.budget_transactions,
                    key=lambda item: (
                        BUDGET_TRANSACTION_ORDER[item.category],
                        item.created_at,
                        str(item.id),
                    ),
                )
            ],
        )

    def _to_read(self, season: Season) -> SeasonRead:
        return self.to_read(season)

    @staticmethod
    def _to_summary_read(season: Season) -> SeasonSummaryRead:
        stage_reads = [
            SeasonService._stage_to_read(stage)
            for stage in sorted(season.stages, key=lambda item: item.stage_number)
        ]
        return SeasonSummaryRead(
            id=season.id,
            user_id=season.user_id,
            name=season.name,
            year=season.year,
            status=season.status,
            current_stage_id=season.current_stage_id,
            current_stage=next(
                (stage for stage in stage_reads if stage.id == season.current_stage_id), None
            ),
            selected_team=TeamRead.model_validate(season.selected_team)
            if season.selected_team is not None
            else None,
            budget=SeasonService._budget_to_read(season),
            created_at=season.created_at,
            updated_at=season.updated_at,
        )

    @staticmethod
    def _stage_to_read(stage: SeasonStage) -> SeasonStageRead:
        weather_payload = (
            build_weather_payload(stage.weather_scenario)
            if stage.status != StageStatus.LOCKED and stage.weather_scenario
            else None
        )
        strategies = (
            build_tire_strategies(stage.track, weather_payload)
            if stage.track is not None and weather_payload is not None
            else None
        )
        starting_compound = (
            recommended_starting_compound(
                stage.track,
                weather_payload,
                strategies,
                stage.weather_scenario,
            )
            if stage.track is not None and weather_payload is not None
            else None
        )
        return SeasonStageRead(
            id=stage.id,
            track_id=stage.track_id,
            stage_number=stage.stage_number,
            weekend_date=stage.weekend_date,
            status=stage.status,
            practice_status=stage.practice_status,
            qualifying_status=stage.qualifying_status,
            race_status=stage.race_status,
            practice_program=PracticeProgramRead(
                stage_id=stage.id,
                fp1_status=stage.fp1_status,
                fp2_status=stage.fp2_status,
                fp3_status=stage.fp3_status,
                practice_completion_status=stage.practice_completion_status,
            ),
            latest_completed_session=SeasonService._latest_completed_session(stage),
            track=TrackRead.model_validate(stage.track) if stage.track is not None else None,
            weather=weather_payload,
            tire_strategies=[
                TireStrategyRead(
                    number=strategy.number,
                    pit_stop_count=strategy.pit_stop_count,
                    stints=[
                        TireStrategyStintRead(
                            compound=stint.compound,
                            start_lap=stint.start_lap,
                            end_lap=stint.end_lap,
                            pit_window_start_lap=stint.pit_window_start_lap,
                            pit_window_end_lap=stint.pit_window_end_lap,
                        )
                        for stint in strategy.stints
                    ],
                )
                for strategy in strategies
            ]
            if strategies is not None
            else None,
            recommended_starting_compound=starting_compound,
        )

    @staticmethod
    def _latest_completed_session(stage: SeasonStage) -> SessionType | None:
        if stage.race_status == StageStatus.COMPLETED:
            return SessionType.RACE
        if stage.qualifying_status == StageStatus.COMPLETED:
            return SessionType.QUALIFYING
        if stage.practice_status == StageStatus.COMPLETED:
            return SessionType.PRACTICE
        return None

    @staticmethod
    def _budget_to_read(season: Season) -> BudgetStateRead:
        return BudgetStateRead(
            starting_budget_millions=float(season.starting_budget_millions),
            spent_budget_millions=float(season.spent_budget_millions),
            available_budget_millions=float(season.available_budget_millions),
            repair_reserve_millions=float(season.repair_reserve_millions),
            setup_reserve_millions=float(season.setup_reserve_millions),
            free_budget_millions=float(free_budget(season)),
        )
