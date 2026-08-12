from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUserDependency, SeasonServiceDependency
from app.schemas.season import (
    BudgetTransactionRead,
    RosterConfirmRequest,
    SeasonCreate,
    SeasonRead,
    SeasonSummaryRead,
    SessionRead,
    UserRead,
)

router = APIRouter(tags=["seasons"])


@router.get("/seasons", response_model=list[SeasonSummaryRead], summary="List seasons")
def list_seasons(
    user: CurrentUserDependency,
    service: SeasonServiceDependency,
) -> list[SeasonSummaryRead]:
    return service.list_seasons(user)


@router.get("/session", response_model=SessionRead, summary="Get current dev session")
def read_session(
    user: CurrentUserDependency,
    service: SeasonServiceDependency,
) -> SessionRead:
    active_season = (
        service.get_season(user.active_season_id, user)
        if user.active_season_id is not None
        else None
    )
    return SessionRead(
        user=UserRead.model_validate(user),
        active_season_id=user.active_season_id,
        active_season=active_season,
    )


@router.post(
    "/seasons",
    response_model=SeasonRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create MVP season",
)
def create_season(
    payload: SeasonCreate,
    user: CurrentUserDependency,
    service: SeasonServiceDependency,
) -> SeasonRead:
    return service.create_season(payload, user)


@router.get("/seasons/{season_id}", response_model=SeasonRead, summary="Get season")
def read_season(
    season_id: UUID,
    user: CurrentUserDependency,
    service: SeasonServiceDependency,
) -> SeasonRead:
    return service.get_season(season_id, user)


@router.get(
    "/seasons/{season_id}/budget-transactions",
    response_model=list[BudgetTransactionRead],
    summary="Get season budget history",
)
def read_budget_transactions(
    season_id: UUID,
    user: CurrentUserDependency,
    service: SeasonServiceDependency,
) -> list[BudgetTransactionRead]:
    return service.get_budget_transactions(season_id, user)


@router.post(
    "/seasons/{season_id}/restart",
    response_model=SeasonRead,
    summary="Start new season after completion",
)
def restart_season(
    season_id: UUID,
    user: CurrentUserDependency,
    service: SeasonServiceDependency,
) -> SeasonRead:
    return service.restart_season(season_id, user)


@router.post(
    "/seasons/{season_id}/roster",
    response_model=SeasonRead,
    summary="Confirm season roster",
)
def confirm_roster(
    season_id: UUID,
    payload: RosterConfirmRequest,
    user: CurrentUserDependency,
    service: SeasonServiceDependency,
) -> SeasonRead:
    return service.confirm_roster(season_id, payload.driver_ids, payload.team_id, user)
