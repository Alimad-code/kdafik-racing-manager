from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUserDependency, StageSessionServiceDependency
from app.domain.enums import PracticeSegment, SessionType
from app.schemas.stage_session import (
    CarSetupSaveRequest,
    CarSetupSaveResponse,
    PracticeProgramResponse,
    QualifyingRunResponse,
    RaceRunResponse,
)
from app.schemas.standings import RepairCarResponse, StandingsRead

router = APIRouter(tags=["stage-sessions"])


@router.post(
    "/seasons/{season_id}/stages/{stage_id}/car-setups",
    response_model=CarSetupSaveResponse,
    summary="Save car setup for a session",
)
def save_car_setups(
    season_id: UUID,
    stage_id: UUID,
    payload: CarSetupSaveRequest,
    user: CurrentUserDependency,
    service: StageSessionServiceDependency,
) -> CarSetupSaveResponse:
    return service.save_car_setups(season_id, stage_id, payload, user)


@router.get(
    "/seasons/{season_id}/stages/{stage_id}/car-setups",
    response_model=CarSetupSaveResponse,
    summary="Get saved car setup for a session",
)
def read_car_setups(
    season_id: UUID,
    stage_id: UUID,
    user: CurrentUserDependency,
    service: StageSessionServiceDependency,
    applies_to_session: Annotated[
        SessionType,
        Query(alias="appliesToSession"),
    ] = SessionType.PRACTICE,
) -> CarSetupSaveResponse:
    return service.get_car_setups(season_id, stage_id, applies_to_session, user)


@router.post(
    "/seasons/{season_id}/stages/{stage_id}/practice/{segment}/run",
    response_model=PracticeProgramResponse,
    summary="Run a specific practice segment",
)
def run_practice_segment(
    season_id: UUID,
    stage_id: UUID,
    segment: PracticeSegment,
    user: CurrentUserDependency,
    service: StageSessionServiceDependency,
) -> PracticeProgramResponse:
    return service.run_practice_segment(season_id, stage_id, segment, user)


@router.post(
    "/seasons/{season_id}/stages/{stage_id}/practice/complete",
    response_model=PracticeProgramResponse,
    summary="Complete practice program",
)
def complete_practice(
    season_id: UUID,
    stage_id: UUID,
    user: CurrentUserDependency,
    service: StageSessionServiceDependency,
) -> PracticeProgramResponse:
    return service.complete_practice(season_id, stage_id, user)


@router.get(
    "/seasons/{season_id}/stages/{stage_id}/practice",
    response_model=PracticeProgramResponse,
    summary="Get practice program and results",
)
def read_practice_results(
    season_id: UUID,
    stage_id: UUID,
    user: CurrentUserDependency,
    service: StageSessionServiceDependency,
) -> PracticeProgramResponse:
    return service.get_practice_results(season_id, stage_id, user)


@router.post(
    "/seasons/{season_id}/stages/{stage_id}/qualifying/run",
    response_model=QualifyingRunResponse,
    summary="Run qualifying session",
)
def run_qualifying(
    season_id: UUID,
    stage_id: UUID,
    user: CurrentUserDependency,
    service: StageSessionServiceDependency,
) -> QualifyingRunResponse:
    return service.run_qualifying(season_id, stage_id, user)


@router.get(
    "/seasons/{season_id}/stages/{stage_id}/qualifying",
    response_model=QualifyingRunResponse,
    summary="Get persisted qualifying results",
)
def read_qualifying_results(
    season_id: UUID,
    stage_id: UUID,
    user: CurrentUserDependency,
    service: StageSessionServiceDependency,
) -> QualifyingRunResponse:
    return service.get_qualifying_results(season_id, stage_id, user)


@router.get(
    "/seasons/{season_id}/stages/{stage_id}/race",
    response_model=RaceRunResponse,
    summary="Get persisted race results",
)
def read_race_results(
    season_id: UUID,
    stage_id: UUID,
    user: CurrentUserDependency,
    service: StageSessionServiceDependency,
) -> RaceRunResponse:
    return service.get_race_results(season_id, stage_id, user)


@router.get(
    "/seasons/{season_id}/standings",
    response_model=StandingsRead,
    summary="Get season standings",
)
def read_standings(
    season_id: UUID,
    user: CurrentUserDependency,
    service: StageSessionServiceDependency,
) -> StandingsRead:
    return service.get_standings(season_id, user)


@router.post(
    "/seasons/{season_id}/cars/{car_id}/repair",
    response_model=RepairCarResponse,
    summary="Repair damaged car",
)
def repair_car(
    season_id: UUID,
    car_id: UUID,
    user: CurrentUserDependency,
    service: StageSessionServiceDependency,
) -> RepairCarResponse:
    return service.repair_car(season_id, car_id, user)
