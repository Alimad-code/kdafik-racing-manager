from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.constants import REPAIR_RESERVE_MULTIPLIER, SEASON_SETUP_CHANGE_COUNT
from app.domain.enums import TrackProfile, TrackSegmentType
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.car import Car
    from app.models.results import SessionResult
    from app.models.season import Season, SeasonStage


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (
        CheckConstraint("pace >= 1 AND pace <= 100", name="ck_drivers_pace_range"),
        CheckConstraint("stability >= 1 AND stability <= 100", name="ck_drivers_stability_range"),
        CheckConstraint("price_millions >= 0", name="ck_drivers_price_non_negative"),
        Index("ix_drivers_is_active", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    number: Mapped[int]
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    code: Mapped[str] = mapped_column(String(3), unique=True)
    nationality: Mapped[str] = mapped_column(String(80))
    price_millions: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    pace: Mapped[int]
    stability: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)

    cars: Mapped[list[Car]] = relationship(back_populates="driver")
    session_results: Mapped[list[SessionResult]] = relationship(
        secondary="season_cars",
        primaryjoin="Driver.id == Car.driver_id",
        secondaryjoin="Car.id == SessionResult.car_id",
        viewonly=True,
    )


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        CheckConstraint(
            "engine_power >= 1 AND engine_power <= 100", name="ck_teams_engine_power_range"
        ),
        CheckConstraint(
            "aero_efficiency >= 1 AND aero_efficiency <= 100", name="ck_teams_aero_efficiency_range"
        ),
        CheckConstraint(
            "chassis_grip >= 1 AND chassis_grip <= 100", name="ck_teams_chassis_grip_range"
        ),
        CheckConstraint(
            "reliability >= 1 AND reliability <= 100", name="ck_teams_reliability_range"
        ),
        CheckConstraint("price_millions >= 0", name="ck_teams_price_non_negative"),
        CheckConstraint("setup_cost_millions >= 0", name="ck_teams_setup_cost_non_negative"),
        CheckConstraint("repair_cost_millions >= 0", name="ck_teams_repair_cost_non_negative"),
        CheckConstraint(
            "car_build_cost_millions >= 0",
            name="ck_teams_car_build_cost_non_negative",
        ),
        Index("ix_teams_is_active", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    short_name: Mapped[str] = mapped_column(String(40))
    base_country: Mapped[str] = mapped_column(String(80))
    power_unit: Mapped[str] = mapped_column(String(80))
    color: Mapped[str] = mapped_column(String(32))
    price_millions: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    engine_power: Mapped[int]
    aero_efficiency: Mapped[int]
    chassis_grip: Mapped[int]
    reliability: Mapped[int]
    setup_cost_millions: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    repair_cost_millions: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    car_build_cost_millions: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    is_active: Mapped[bool] = mapped_column(default=True)

    seasons: Mapped[list[Season]] = relationship(back_populates="selected_team")
    cars: Mapped[list[Car]] = relationship(back_populates="team")

    @property
    def minimum_repair_reserve_millions(self) -> Decimal:
        return self.repair_cost_millions * REPAIR_RESERVE_MULTIPLIER

    @property
    def minimum_setup_reserve_millions(self) -> Decimal:
        return self.setup_cost_millions * SEASON_SETUP_CHANGE_COUNT

    @property
    def minimum_reserve_millions(self) -> Decimal:
        return self.minimum_repair_reserve_millions + self.minimum_setup_reserve_millions

    @property
    def car_rating(self) -> int:
        return round((self.engine_power + self.aero_efficiency + self.chassis_grip) / 3)


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        CheckConstraint("laps > 0", name="ck_tracks_laps_positive"),
        CheckConstraint("length_km > 0", name="ck_tracks_length_positive"),
        CheckConstraint("track_length_meters > 0", name="ck_tracks_track_length_meters_positive"),
        CheckConstraint(
            "rain_probability >= 0 AND rain_probability <= 1",
            name="ck_tracks_rain_probability_range",
        ),
        CheckConstraint(
            "track_temperature_min_c <= track_temperature_max_c",
            name="ck_tracks_temperature_range_order",
        ),
        CheckConstraint(
            "variability >= 0 AND variability <= 1", name="ck_tracks_variability_range"
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80))
    laps: Mapped[int]
    length_km: Mapped[Decimal] = mapped_column(Numeric(5, 3))
    svg_path: Mapped[str] = mapped_column(Text)
    track_length_meters: Mapped[Decimal] = mapped_column(Numeric(8, 1))
    rain_probability: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    track_temperature_min_c: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    track_temperature_max_c: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    variability: Mapped[Decimal] = mapped_column(Numeric(4, 3))

    stages: Mapped[list[SeasonStage]] = relationship(back_populates="track")
    segments: Mapped[list[TrackSegment]] = relationship(
        back_populates="track",
        cascade="all, delete-orphan",
        order_by="TrackSegment.segment_index",
    )

    @property
    def climate(self) -> dict[str, float]:
        return {
            "rainProbability": float(self.rain_probability),
            "trackTemperatureMinC": float(self.track_temperature_min_c),
            "trackTemperatureMaxC": float(self.track_temperature_max_c),
            "variability": float(self.variability),
        }

    @property
    def profile(self) -> TrackProfile:
        if not self.segments:
            return TrackProfile.BALANCED

        corner_length = sum(
            float(segment.length_meters)
            for segment in self.segments
            if segment.type != TrackSegmentType.STRAIGHT
        )
        corner_ratio = corner_length / float(self.track_length_meters)
        if corner_ratio < 0.35:
            return TrackProfile.SPEED
        if corner_ratio > 0.62:
            return TrackProfile.TECHNICAL
        return TrackProfile.BALANCED


class TrackSegment(Base):
    __tablename__ = "track_segments"
    __table_args__ = (
        UniqueConstraint("track_id", "segment_index", name="uq_track_segments_track_order"),
        CheckConstraint("segment_index > 0", name="ck_track_segments_index_positive"),
        CheckConstraint("length_meters > 0", name="ck_track_segments_length_positive"),
        CheckConstraint("base_speed > 0", name="ck_track_segments_base_speed_positive"),
        CheckConstraint(
            "overtake_chance >= 0 AND overtake_chance <= 1",
            name="ck_track_segments_overtake_chance_range",
        ),
        Index("ix_track_segments_track_id", "track_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tracks.id", ondelete="CASCADE"),
    )
    segment_index: Mapped[int]
    type: Mapped[TrackSegmentType] = mapped_column(
        enum_type(TrackSegmentType, "track_segment_type", 32)
    )
    length_meters: Mapped[Decimal] = mapped_column(Numeric(8, 1))
    base_speed: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    overtake_chance: Mapped[Decimal] = mapped_column(Numeric(4, 3))

    track: Mapped[Track] = relationship(back_populates="segments")
