from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import CarCondition, SessionType, SetupBand
from app.models.mixins import TimestampMixin
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.catalog import Driver, Team
    from app.models.results import SessionResult
    from app.models.season import Season, SeasonStage


class Car(TimestampMixin, Base):
    __tablename__ = "season_cars"
    __table_args__ = (
        UniqueConstraint("season_id", "driver_id", name="uq_cars_season_driver"),
        UniqueConstraint("season_id", "slot", name="uq_cars_season_slot"),
        CheckConstraint("slot > 0", name="ck_cars_slot_positive"),
        CheckConstraint(
            "engine_power >= 1 AND engine_power <= 100", name="ck_cars_engine_power_range"
        ),
        CheckConstraint(
            "aero_efficiency >= 1 AND aero_efficiency <= 100", name="ck_cars_aero_efficiency_range"
        ),
        CheckConstraint(
            "chassis_grip >= 1 AND chassis_grip <= 100", name="ck_cars_chassis_grip_range"
        ),
        CheckConstraint(
            "reliability >= 1 AND reliability <= 100", name="ck_cars_reliability_range"
        ),
        CheckConstraint(
            "wings_setting >= 0 AND wings_setting <= 100",
            name="ck_cars_wings_range",
        ),
        CheckConstraint(
            "suspension_setting >= 0 AND suspension_setting <= 100",
            name="ck_cars_suspension_range",
        ),
        CheckConstraint(
            "gearbox_setting >= 0 AND gearbox_setting <= 100",
            name="ck_cars_gearbox_range",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 100", name="ck_cars_confidence_range"),
        Index("ix_cars_season_id", "season_id"),
        Index("ix_cars_team_id", "team_id"),
        Index("ix_cars_driver_id", "driver_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    season_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("seasons.id", ondelete="CASCADE"),
    )
    team_id: Mapped[str] = mapped_column(String(64), ForeignKey("teams.id", ondelete="RESTRICT"))
    driver_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("drivers.id", ondelete="RESTRICT"),
    )
    slot: Mapped[int]
    is_player: Mapped[bool] = mapped_column(default=False)
    driver_first_name_snapshot: Mapped[str] = mapped_column(String(80))
    driver_last_name_snapshot: Mapped[str] = mapped_column(String(80))
    driver_code_snapshot: Mapped[str] = mapped_column(String(3))
    team_name_snapshot: Mapped[str] = mapped_column(String(120))
    team_short_name_snapshot: Mapped[str] = mapped_column(String(40))
    team_color_snapshot: Mapped[str] = mapped_column(String(32))
    engine_power: Mapped[int]
    aero_efficiency: Mapped[int]
    chassis_grip: Mapped[int]
    reliability: Mapped[int]
    condition: Mapped[CarCondition] = mapped_column(
        enum_type(CarCondition, "car_condition", 32),
        default=CarCondition.HEALTHY,
    )
    wings_setting: Mapped[int] = mapped_column(default=50)
    suspension_setting: Mapped[int] = mapped_column(default=50)
    gearbox_setting: Mapped[int] = mapped_column(default=50)
    confidence: Mapped[int] = mapped_column(default=50)

    season: Mapped[Season] = relationship(back_populates="cars")
    team: Mapped[Team] = relationship(back_populates="cars")
    driver: Mapped[Driver] = relationship(back_populates="cars")
    setups: Mapped[list[CarSetup]] = relationship(
        back_populates="car",
        cascade="all, delete-orphan",
    )
    session_results: Mapped[list[SessionResult]] = relationship(back_populates="car")

    @property
    def team_color(self) -> str:
        return self.team_color_snapshot

    @property
    def driver_code(self) -> str:
        return self.driver_code_snapshot


class CarSetup(Base):
    __tablename__ = "car_setups"
    __table_args__ = (
        UniqueConstraint(
            "stage_id",
            "car_id",
            "applies_to_session",
            name="uq_car_setups_stage_car_session",
        ),
        CheckConstraint(
            "wings_setting >= 0 AND wings_setting <= 100",
            name="ck_car_setups_wings_range",
        ),
        CheckConstraint(
            "suspension_setting >= 0 AND suspension_setting <= 100",
            name="ck_car_setups_suspension_range",
        ),
        CheckConstraint(
            "gearbox_setting >= 0 AND gearbox_setting <= 100",
            name="ck_car_setups_gearbox_range",
        ),
        CheckConstraint("cost_millions >= 0", name="ck_car_setups_cost_non_negative"),
        Index("ix_car_setups_stage_id", "stage_id"),
        Index("ix_car_setups_car_id", "car_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    stage_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("season_stages.id", ondelete="CASCADE"),
    )
    car_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("season_cars.id", ondelete="CASCADE"))
    wings_setting: Mapped[int]
    suspension_setting: Mapped[int]
    gearbox_setting: Mapped[int]
    setup_band: Mapped[SetupBand] = mapped_column(enum_type(SetupBand, "setup_band", 32))
    cost_millions: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0.00"))
    applies_to_session: Mapped[SessionType] = mapped_column(
        enum_type(SessionType, "setup_session_type", 32)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    stage: Mapped[SeasonStage] = relationship(back_populates="car_setups")
    car: Mapped[Car] = relationship(back_populates="setups")

    @property
    def season_id(self) -> UUID:
        return self.stage.season_id
