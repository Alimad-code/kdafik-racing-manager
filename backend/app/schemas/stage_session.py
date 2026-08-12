from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import (
    EventSeverity,
    PracticeSegment,
    RaceEventType,
    ResultStatus,
    SessionType,
    SetupBand,
)
from app.schemas.season import (
    PracticeProgramRead,
    SeasonRead,
    SeasonSchema,
    SeasonStageRead,
)
from app.schemas.standings import StandingsRead


class CarSetupInput(SeasonSchema):
    car_id: UUID
    wings_setting: int = Field(ge=0, le=100)
    suspension_setting: int = Field(ge=0, le=100)
    gearbox_setting: int = Field(ge=0, le=100)


class CarSetupSaveRequest(SeasonSchema):
    setups: list[CarSetupInput] = Field(min_length=1)
    applies_to_session: SessionType = SessionType.PRACTICE


class CarSetupRead(SeasonSchema):
    id: UUID
    season_id: UUID
    stage_id: UUID
    car_id: UUID
    wings_setting: int
    suspension_setting: int
    gearbox_setting: int
    setup_band: SetupBand
    cost_millions: float
    applies_to_session: SessionType
    created_at: datetime


class PracticeResultRead(SeasonSchema):
    id: UUID
    season_id: UUID
    stage_id: UUID
    practice_segment: PracticeSegment
    driver_id: str
    team_id: str
    team_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    car_id: UUID
    position: int
    best_lap: str | None
    gap: str
    laps: int
    points: int
    status: ResultStatus
    event: RaceEventType | None
    reason: str | None
    setup_feedback: str | None
    engineer_recommendation: str | None


class QualifyingResultRead(SeasonSchema):
    id: UUID
    season_id: UUID
    stage_id: UUID
    driver_id: str
    team_id: str
    team_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    car_id: UUID
    position: int
    best_lap: str | None
    gap: str
    laps: int
    points: int
    status: ResultStatus
    event: RaceEventType | None
    reason: str | None


class RaceResultRead(SeasonSchema):
    id: UUID
    season_id: UUID
    stage_id: UUID
    driver_id: str
    team_id: str
    team_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    car_id: UUID
    grid_position: int
    finish_position: int
    best_lap: str | None
    best_lap_number: int | None = Field(default=None, ge=1)
    max_speed_kph: float | None = Field(default=None, ge=0)
    gap: str
    laps: int
    points: int
    status: ResultStatus
    event: RaceEventType | None
    reason: str | None


class RaceEventRead(SeasonSchema):
    id: UUID
    season_id: UUID
    stage_id: UUID
    session_type: SessionType
    driver_id: str | None
    car_id: UUID | None
    type: RaceEventType
    description: str
    severity: EventSeverity
    created_at: datetime


class CarSetupSaveResponse(SeasonSchema):
    season: SeasonRead
    stage: SeasonStageRead
    setups: list[CarSetupRead]


class PracticeProgramResponse(SeasonSchema):
    season: SeasonRead
    stage: SeasonStageRead
    practice_program: PracticeProgramRead
    practice_results: list[PracticeResultRead]


class QualifyingRunResponse(SeasonSchema):
    season: SeasonRead
    stage: SeasonStageRead
    qualifying_results: list[QualifyingResultRead]


class RaceRunResponse(SeasonSchema):
    season: SeasonRead
    stage: SeasonStageRead
    race_results: list[RaceResultRead]
    events: list[RaceEventRead]
    standings: StandingsRead
