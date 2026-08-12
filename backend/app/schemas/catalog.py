from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import TrackProfile


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class CatalogSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )


class DriverRead(CatalogSchema):
    id: str
    number: int
    first_name: str
    last_name: str
    code: str
    nationality: str
    price_millions: float
    pace: int
    stability: int


class TeamRead(CatalogSchema):
    id: str
    name: str
    short_name: str
    base_country: str
    power_unit: str
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    price_millions: float
    car_rating: int = Field(ge=1, le=100)
    engine_power: int
    aero_efficiency: int
    chassis_grip: int
    reliability: int
    setup_cost_millions: float
    repair_cost_millions: float
    car_build_cost_millions: float
    minimum_repair_reserve_millions: float
    minimum_setup_reserve_millions: float
    minimum_reserve_millions: float


class ClimateProfileRead(CatalogSchema):
    rain_probability: float = Field(ge=0, le=1)
    track_temperature_min_c: float
    track_temperature_max_c: float
    variability: float = Field(ge=0, le=1)


class TrackRead(CatalogSchema):
    id: str
    name: str
    country: str
    profile: TrackProfile
    laps: int
    length_km: float
    svg_path: str
    climate: ClimateProfileRead


class CalendarStageRead(CatalogSchema):
    stage_number: int
    track_id: str
    weekend_date: date


class CatalogRead(CatalogSchema):
    drivers: list[DriverRead]
    teams: list[TeamRead]
    tracks: list[TrackRead]
    calendar: list[CalendarStageRead]
