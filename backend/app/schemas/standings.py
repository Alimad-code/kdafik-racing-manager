from uuid import UUID

from app.schemas.catalog import DriverRead, TeamRead
from app.schemas.season import BudgetTransactionRead, CarRead, SeasonRead, SeasonSchema


class DriverStandingRead(SeasonSchema):
    id: UUID
    season_id: UUID
    driver_id: str
    team_id: str
    position: int
    points: int
    wins: int
    podiums: int
    driver: DriverRead | None = None
    team: TeamRead | None = None


class ConstructorStandingRead(SeasonSchema):
    id: UUID
    season_id: UUID
    team_id: str
    position: int
    points: int
    wins: int
    podiums: int
    team: TeamRead | None = None


class StandingsRead(SeasonSchema):
    driver_standings: list[DriverStandingRead]
    constructor_standings: list[ConstructorStandingRead]
    selected_team_rank: int | None


class RepairCarResponse(SeasonSchema):
    season: SeasonRead
    car: CarRead
    transaction: BudgetTransactionRead
