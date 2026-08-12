from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    EventSeverity,
    PracticeSegment,
    RaceEventType,
    ResultStatus,
    SessionType,
    StageSessionType,
)
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.car import Car
    from app.models.season import StageSession


class SessionResult(Base):
    __tablename__ = "session_results"
    __table_args__ = (
        UniqueConstraint("stage_session_id", "car_id", name="uq_session_results_session_car"),
        CheckConstraint("position > 0", name="ck_session_results_position_positive"),
        CheckConstraint(
            "grid_position IS NULL OR grid_position > 0",
            name="ck_session_results_grid_positive",
        ),
        CheckConstraint("laps >= 0", name="ck_session_results_laps_non_negative"),
        CheckConstraint("points >= 0", name="ck_session_results_points_non_negative"),
        CheckConstraint(
            "best_lap_number IS NULL OR best_lap_number > 0",
            name="ck_session_results_best_lap_number_positive",
        ),
        CheckConstraint(
            "max_speed_kph IS NULL OR max_speed_kph >= 0",
            name="ck_session_results_max_speed_kph_non_negative",
        ),
        Index("ix_session_results_stage_session_id", "stage_session_id"),
        Index("ix_session_results_car_id", "car_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    stage_session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("stage_sessions.id", ondelete="CASCADE"),
    )
    car_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("season_cars.id", ondelete="CASCADE"),
    )
    position: Mapped[int]
    grid_position: Mapped[int | None]
    best_lap: Mapped[str | None] = mapped_column(String(24))
    best_lap_number: Mapped[int | None] = mapped_column(nullable=True)
    max_speed_kph: Mapped[float | None] = mapped_column(Float, nullable=True)
    gap: Mapped[str] = mapped_column(String(32), default="")
    laps: Mapped[int]
    points: Mapped[int] = mapped_column(default=0)
    status: Mapped[ResultStatus] = mapped_column(enum_type(ResultStatus, "result_status", 32))
    event: Mapped[RaceEventType | None] = mapped_column(
        enum_type(RaceEventType, "result_event", 32)
    )
    reason: Mapped[str | None] = mapped_column(Text)
    setup_feedback: Mapped[str | None] = mapped_column(Text)
    engineer_recommendation: Mapped[str | None] = mapped_column(Text)
    event_description: Mapped[str | None] = mapped_column(Text)
    event_severity: Mapped[EventSeverity | None] = mapped_column(
        enum_type(EventSeverity, "event_severity", 32)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    stage_session: Mapped[StageSession] = relationship(back_populates="results")
    car: Mapped[Car] = relationship(back_populates="session_results")

    @property
    def season_id(self) -> UUID:
        return self.stage_session.stage.season_id

    @property
    def stage_id(self) -> UUID:
        return self.stage_session.stage_id

    @property
    def practice_segment(self) -> PracticeSegment | None:
        mapping = {
            StageSessionType.FP1: PracticeSegment.FP1,
            StageSessionType.FP2: PracticeSegment.FP2,
            StageSessionType.FP3: PracticeSegment.FP3,
        }
        return mapping.get(self.stage_session.type)

    @property
    def session_type(self) -> SessionType:
        if self.stage_session.type == StageSessionType.QUALIFYING:
            return SessionType.QUALIFYING
        if self.stage_session.type == StageSessionType.RACE:
            return SessionType.RACE
        return SessionType.PRACTICE

    @property
    def driver_id(self) -> str:
        return self.car.driver_id

    @property
    def team_id(self) -> str:
        return self.car.team_id

    @property
    def team_color(self) -> str:
        return self.car.team_color

    @property
    def finish_position(self) -> int:
        return self.position

    @property
    def type(self) -> RaceEventType | None:
        return self.event

    @property
    def description(self) -> str:
        return self.event_description or self.reason or ""

    @property
    def severity(self) -> EventSeverity:
        return self.event_severity or EventSeverity.INFO
