from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    BudgetCategory,
    CarCondition,
    PracticeCompletionStatus,
    PracticeSegmentStatus,
    SeasonStatus,
    SessionType,
    StageStatus,
)
from app.schemas.catalog import DriverRead, TeamRead, TrackRead, to_camel


class SeasonSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )


class SeasonCreate(SeasonSchema):
    name: str = Field(default="MVP Season", min_length=1, max_length=120)
    year: int = Field(default=2026, ge=2000, le=2100)


class RosterConfirmRequest(SeasonSchema):
    driver_ids: list[str]
    team_id: str = Field(min_length=1)


class BudgetStateRead(SeasonSchema):
    starting_budget_millions: float
    spent_budget_millions: float
    available_budget_millions: float
    repair_reserve_millions: float
    setup_reserve_millions: float
    free_budget_millions: float


class PracticeProgramRead(SeasonSchema):
    stage_id: UUID
    fp1_status: PracticeSegmentStatus
    fp2_status: PracticeSegmentStatus
    fp3_status: PracticeSegmentStatus
    practice_completion_status: PracticeCompletionStatus


class WeatherSnapshotRead(SeasonSchema):
    precipitation: Literal["none", "light", "moderate", "heavy"]
    track_temp: float
    rain_intensity: float = Field(ge=0, le=1)
    track_wetness: float = Field(ge=0, le=1)


class PracticeWeatherRead(SeasonSchema):
    fp1: WeatherSnapshotRead
    fp2: WeatherSnapshotRead
    fp3: WeatherSnapshotRead


class RaceForecastPointRead(SeasonSchema):
    point: str
    progress: float = Field(ge=0, le=1)
    temperature_min_c: float
    temperature_max_c: float
    rain_chance: float = Field(ge=0, le=1)
    expected_rain: Literal["none", "light", "moderate", "heavy"]
    track_wetness_min: float = Field(ge=0, le=1)
    track_wetness_max: float = Field(ge=0, le=1)
    track_temp: float
    confidence: str


class StageWeatherRead(SeasonSchema):
    practice: PracticeWeatherRead
    qualifying: WeatherSnapshotRead
    race_forecast: list[RaceForecastPointRead] = Field(min_length=4, max_length=4)


class TireStrategyStintRead(SeasonSchema):
    compound: str
    start_lap: int = Field(ge=1)
    end_lap: int = Field(ge=1)
    pit_window_start_lap: int | None = Field(default=None, ge=1)
    pit_window_end_lap: int | None = Field(default=None, ge=1)


class TireStrategyRead(SeasonSchema):
    number: int = Field(ge=1, le=3)
    pit_stop_count: int = Field(ge=1, le=3)
    stints: list[TireStrategyStintRead] = Field(min_length=2, max_length=4)


class BudgetTransactionRead(SeasonSchema):
    id: UUID
    category: BudgetCategory
    label: str
    amount_millions: float
    balance_before_millions: float
    balance_after_millions: float
    reference_type: str | None
    reference_id: str | None
    created_at: datetime


class CarRead(SeasonSchema):
    id: UUID
    team_id: str
    team_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    driver_id: str
    engine_power: int
    aero_efficiency: int
    chassis_grip: int
    reliability: int
    condition: CarCondition
    wings_setting: int
    suspension_setting: int
    gearbox_setting: int
    confidence: int


class SeasonStageRead(SeasonSchema):
    id: UUID
    track_id: str
    stage_number: int
    weekend_date: date
    status: StageStatus
    practice_status: StageStatus
    qualifying_status: StageStatus
    race_status: StageStatus
    practice_program: PracticeProgramRead | None = None
    latest_completed_session: SessionType | None = None
    track: TrackRead | None = None
    weather: StageWeatherRead | None = None
    tire_strategies: list[TireStrategyRead] | None = None
    recommended_starting_compound: (
        Literal["Soft", "Medium", "Hard", "Intermediate", "Wet"] | None
    ) = None


class UserRead(SeasonSchema):
    id: UUID
    display_name: str
    email: str | None
    role: str
    active_season_id: UUID | None


class SeasonSummaryRead(SeasonSchema):
    id: UUID
    user_id: UUID
    name: str
    year: int
    status: SeasonStatus
    current_stage_id: UUID | None
    current_stage: SeasonStageRead | None
    selected_team: TeamRead | None
    budget: BudgetStateRead
    created_at: datetime
    updated_at: datetime


class SeasonRead(SeasonSchema):
    id: UUID
    user_id: UUID
    name: str
    year: int
    status: SeasonStatus
    selected_team_id: str | None
    current_stage_id: UUID | None
    current_stage: SeasonStageRead | None
    budget: BudgetStateRead
    selected_drivers: list[DriverRead]
    selected_team: TeamRead | None
    cars: list[CarRead]
    stages: list[SeasonStageRead]
    budget_transactions: list[BudgetTransactionRead]


class SessionRead(SeasonSchema):
    user: UserRead
    active_season_id: UUID | None
    active_season: SeasonRead | None = None
