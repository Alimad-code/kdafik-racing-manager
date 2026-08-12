from app.repositories.catalog import CatalogRepository
from app.schemas.catalog import CalendarStageRead, CatalogRead, DriverRead, TeamRead, TrackRead
from app.seed import MVP_CALENDAR


class CatalogService:
    def __init__(self, repository: CatalogRepository) -> None:
        self.repository = repository

    def list_drivers(self) -> list[DriverRead]:
        return [
            DriverRead.model_validate(driver) for driver in self.repository.list_active_drivers()
        ]

    def list_teams(self) -> list[TeamRead]:
        return [TeamRead.model_validate(team) for team in self.repository.list_active_teams()]

    def list_tracks(self) -> list[TrackRead]:
        return [TrackRead.model_validate(track) for track in self.repository.list_tracks()]

    def list_calendar(self) -> list[CalendarStageRead]:
        return [CalendarStageRead.model_validate(stage) for stage in MVP_CALENDAR]

    def get_catalog(self) -> CatalogRead:
        return CatalogRead(
            drivers=self.list_drivers(),
            teams=self.list_teams(),
            tracks=self.list_tracks(),
            calendar=self.list_calendar(),
        )
