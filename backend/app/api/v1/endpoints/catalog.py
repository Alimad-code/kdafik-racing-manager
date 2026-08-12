from fastapi import APIRouter

from app.api.dependencies import CatalogServiceDependency
from app.schemas.catalog import CalendarStageRead, CatalogRead, DriverRead, TeamRead, TrackRead

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("", response_model=CatalogRead, summary="Get complete MVP catalog")
def read_catalog(service: CatalogServiceDependency) -> CatalogRead:
    return service.get_catalog()


@router.get("/drivers", response_model=list[DriverRead], summary="List active drivers")
def read_drivers(service: CatalogServiceDependency) -> list[DriverRead]:
    return service.list_drivers()


@router.get("/teams", response_model=list[TeamRead], summary="List active teams")
def read_teams(service: CatalogServiceDependency) -> list[TeamRead]:
    return service.list_teams()


@router.get("/tracks", response_model=list[TrackRead], summary="List MVP tracks")
def read_tracks(service: CatalogServiceDependency) -> list[TrackRead]:
    return service.list_tracks()


@router.get("/calendar", response_model=list[CalendarStageRead], summary="List MVP calendar")
def read_calendar(service: CatalogServiceDependency) -> list[CalendarStageRead]:
    return service.list_calendar()
