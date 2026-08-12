from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.constants import STARTING_BUDGET_MILLIONS
from app.domain.enums import (
    PracticeCompletionStatus,
    PracticeSegment,
    PracticeSegmentStatus,
    SeasonStatus,
    SessionType,
    StageSessionStatus,
    StageSessionType,
    StageStatus,
)
from app.models.mixins import TimestampMixin
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.budget import BudgetTransaction
    from app.models.car import Car, CarSetup
    from app.models.catalog import Driver, Team, Track
    from app.models.results import SessionResult
    from app.models.user import User


class Season(TimestampMixin, Base):
    __tablename__ = "seasons"
    __table_args__ = (
        CheckConstraint("year >= 2000 AND year <= 2100", name="ck_seasons_year_range"),
        CheckConstraint(
            "starting_budget_millions >= 0",
            name="ck_seasons_starting_budget_non_negative",
        ),
        CheckConstraint(
            "initial_repair_reserve_millions >= 0",
            name="ck_seasons_initial_repair_reserve_non_negative",
        ),
        CheckConstraint(
            "initial_setup_reserve_millions >= 0",
            name="ck_seasons_initial_setup_reserve_non_negative",
        ),
        Index("ix_seasons_user_id", "user_id"),
        Index("ix_seasons_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    name: Mapped[str] = mapped_column(String(120))
    year: Mapped[int]
    status: Mapped[SeasonStatus] = mapped_column(
        enum_type(SeasonStatus, "season_status", 32),
        default=SeasonStatus.SETUP,
    )
    selected_team_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("teams.id", ondelete="RESTRICT"),
    )
    current_stage_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "season_stages.id",
            name="fk_seasons_current_stage_id",
            use_alter=True,
            ondelete="SET NULL",
        ),
    )
    starting_budget_millions: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=STARTING_BUDGET_MILLIONS,
    )
    initial_repair_reserve_millions: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=Decimal("0.00"),
    )
    initial_setup_reserve_millions: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=Decimal("0.00"),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(
        back_populates="seasons",
        foreign_keys=[user_id],
    )
    selected_team: Mapped[Team | None] = relationship(back_populates="seasons")
    current_stage: Mapped[SeasonStage | None] = relationship(
        foreign_keys=[current_stage_id],
        post_update=True,
    )
    stages: Mapped[list[SeasonStage]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
        foreign_keys="SeasonStage.season_id",
        order_by="SeasonStage.stage_number",
    )
    cars: Mapped[list[Car]] = relationship(back_populates="season", cascade="all, delete-orphan")
    budget_transactions: Mapped[list[BudgetTransaction]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
    )

    @property
    def selected_drivers(self) -> list[Driver]:
        return [
            car.driver
            for car in sorted(self.cars, key=lambda item: item.slot)
            if car.is_player and car.driver is not None
        ]

    @property
    def player_cars(self) -> list[Car]:
        return [car for car in sorted(self.cars, key=lambda item: item.slot) if car.is_player]

    @property
    def spent_budget_millions(self) -> Decimal:
        return sum(
            (transaction.amount_millions for transaction in self.budget_transactions),
            Decimal("0.00"),
        )

    @spent_budget_millions.setter
    def spent_budget_millions(self, value: Decimal) -> None:
        self._spent_budget_override = value

    @property
    def available_budget_millions(self) -> Decimal:
        override = getattr(self, "_available_budget_override", None)
        if override is not None:
            return override
        return self.starting_budget_millions - self.spent_budget_millions

    @available_budget_millions.setter
    def available_budget_millions(self, value: Decimal) -> None:
        self._available_budget_override = value

    @property
    def repair_reserve_millions(self) -> Decimal:
        spent = sum(
            (
                transaction.reserve_applied_millions
                for transaction in self.budget_transactions
                if transaction.category.value == "repair"
            ),
            Decimal("0.00"),
        )
        return max(self.initial_repair_reserve_millions - spent, Decimal("0.00"))

    @repair_reserve_millions.setter
    def repair_reserve_millions(self, value: Decimal) -> None:
        self.initial_repair_reserve_millions = value

    @property
    def setup_reserve_millions(self) -> Decimal:
        spent = sum(
            (
                transaction.reserve_applied_millions
                for transaction in self.budget_transactions
                if transaction.category.value == "setup"
            ),
            Decimal("0.00"),
        )
        return max(self.initial_setup_reserve_millions - spent, Decimal("0.00"))

    @setup_reserve_millions.setter
    def setup_reserve_millions(self, value: Decimal) -> None:
        self.initial_setup_reserve_millions = value


class SeasonStage(Base):
    __tablename__ = "season_stages"
    __table_args__ = (
        UniqueConstraint("season_id", "stage_number", name="uq_season_stages_season_stage_number"),
        CheckConstraint(
            "stage_number >= 1 AND stage_number <= 12",
            name="ck_season_stages_stage_number_mvp_range",
        ),
        Index("ix_season_stages_season_id", "season_id"),
        Index("ix_season_stages_track_id", "track_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    season_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("seasons.id", ondelete="CASCADE"),
    )
    track_id: Mapped[str] = mapped_column(String(64), ForeignKey("tracks.id", ondelete="RESTRICT"))
    stage_number: Mapped[int]
    weekend_date: Mapped[date]
    weather_scenario: Mapped[dict] = mapped_column(JSON)
    season: Mapped[Season] = relationship(
        back_populates="stages",
        foreign_keys=[season_id],
    )
    track: Mapped[Track] = relationship(back_populates="stages")
    sessions: Mapped[list[StageSession]] = relationship(
        back_populates="stage",
        cascade="all, delete-orphan",
        order_by="StageSession.sort_order",
    )
    car_setups: Mapped[list[CarSetup]] = relationship(
        back_populates="stage",
        cascade="all, delete-orphan",
    )

    def session_for(self, session_type: StageSessionType) -> StageSession:
        for session in self.sessions:
            if session.type == session_type:
                return session
        session = StageSession(type=session_type, status=StageSessionStatus.LOCKED)
        self.sessions.append(session)
        return session

    @property
    def status(self) -> StageStatus:
        if self.race_status == StageStatus.COMPLETED:
            return StageStatus.COMPLETED
        if any(session.status != StageSessionStatus.LOCKED for session in self.sessions):
            return StageStatus.AVAILABLE
        return StageStatus.LOCKED

    @status.setter
    def status(self, value: StageStatus) -> None:
        if value == StageStatus.LOCKED:
            for session in self.sessions:
                session.status = StageSessionStatus.LOCKED
        elif value == StageStatus.AVAILABLE:
            self.fp1_status = PracticeSegmentStatus.AVAILABLE
        elif value == StageStatus.COMPLETED:
            self.race_status = StageStatus.COMPLETED

    @property
    def practice_status(self) -> StageStatus:
        if self.practice_completion_status == PracticeCompletionStatus.COMPLETED:
            return StageStatus.COMPLETED
        practice_sessions = [
            self.session_for(StageSessionType.FP1),
            self.session_for(StageSessionType.FP2),
            self.session_for(StageSessionType.FP3),
            self.session_for(StageSessionType.PRACTICE_COMPLETION),
        ]
        if any(session.status != StageSessionStatus.LOCKED for session in practice_sessions):
            return StageStatus.AVAILABLE
        return StageStatus.LOCKED

    @practice_status.setter
    def practice_status(self, value: StageStatus) -> None:
        if value == StageStatus.LOCKED:
            for session_type in _PRACTICE_SESSION_TYPES:
                self.session_for(session_type).status = StageSessionStatus.LOCKED
        elif value == StageStatus.AVAILABLE:
            self.fp1_status = PracticeSegmentStatus.AVAILABLE
        elif value == StageStatus.COMPLETED:
            self.practice_completion_status = PracticeCompletionStatus.COMPLETED

    @property
    def fp1_status(self) -> PracticeSegmentStatus:
        return _practice_status(self.session_for(StageSessionType.FP1).status)

    @fp1_status.setter
    def fp1_status(self, value: PracticeSegmentStatus) -> None:
        self.session_for(StageSessionType.FP1).status = StageSessionStatus(value.value)

    @property
    def fp2_status(self) -> PracticeSegmentStatus:
        return _practice_status(self.session_for(StageSessionType.FP2).status)

    @fp2_status.setter
    def fp2_status(self, value: PracticeSegmentStatus) -> None:
        self.session_for(StageSessionType.FP2).status = StageSessionStatus(value.value)

    @property
    def fp3_status(self) -> PracticeSegmentStatus:
        return _practice_status(self.session_for(StageSessionType.FP3).status)

    @fp3_status.setter
    def fp3_status(self, value: PracticeSegmentStatus) -> None:
        self.session_for(StageSessionType.FP3).status = StageSessionStatus(value.value)

    @property
    def practice_completion_status(self) -> PracticeCompletionStatus:
        status = self.session_for(StageSessionType.PRACTICE_COMPLETION).status
        if status == StageSessionStatus.COMPLETED:
            return PracticeCompletionStatus.COMPLETED
        if status == StageSessionStatus.AVAILABLE:
            return PracticeCompletionStatus.AVAILABLE
        return PracticeCompletionStatus.LOCKED

    @practice_completion_status.setter
    def practice_completion_status(self, value: PracticeCompletionStatus) -> None:
        self.session_for(StageSessionType.PRACTICE_COMPLETION).status = StageSessionStatus(
            value.value
        )

    @property
    def qualifying_status(self) -> StageStatus:
        return _stage_status(self.session_for(StageSessionType.QUALIFYING).status)

    @qualifying_status.setter
    def qualifying_status(self, value: StageStatus) -> None:
        self.session_for(StageSessionType.QUALIFYING).status = StageSessionStatus(value.value)

    @property
    def race_status(self) -> StageStatus:
        return _stage_status(self.session_for(StageSessionType.RACE).status)

    @race_status.setter
    def race_status(self, value: StageStatus) -> None:
        self.session_for(StageSessionType.RACE).status = StageSessionStatus(value.value)

    def session_for_practice_segment(self, segment: PracticeSegment) -> StageSession:
        return self.session_for(
            {
                PracticeSegment.FP1: StageSessionType.FP1,
                PracticeSegment.FP2: StageSessionType.FP2,
                PracticeSegment.FP3: StageSessionType.FP3,
            }[segment]
        )

    def session_for_session_type(self, session_type: SessionType) -> StageSession:
        return self.session_for(
            {
                SessionType.PRACTICE: StageSessionType.FP1,
                SessionType.QUALIFYING: StageSessionType.QUALIFYING,
                SessionType.RACE: StageSessionType.RACE,
            }[session_type]
        )


class StageSession(Base):
    __tablename__ = "stage_sessions"
    __table_args__ = (
        UniqueConstraint("stage_id", "type", name="uq_stage_sessions_stage_type"),
        CheckConstraint("sort_order > 0", name="ck_stage_sessions_sort_order_positive"),
        Index("ix_stage_sessions_stage_id", "stage_id"),
        Index("ix_stage_sessions_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    stage_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("season_stages.id", ondelete="CASCADE"),
    )
    type: Mapped[StageSessionType] = mapped_column(
        enum_type(StageSessionType, "stage_session_type", 32)
    )
    status: Mapped[StageSessionStatus] = mapped_column(
        enum_type(StageSessionStatus, "stage_session_status", 32),
        default=StageSessionStatus.LOCKED,
    )
    sort_order: Mapped[int] = mapped_column(default=1)

    stage: Mapped[SeasonStage] = relationship(back_populates="sessions")
    results: Mapped[list[SessionResult]] = relationship(
        back_populates="stage_session",
        cascade="all, delete-orphan",
    )

    @property
    def season_id(self) -> UUID:
        return self.stage.season_id


_PRACTICE_SESSION_TYPES = (
    StageSessionType.FP1,
    StageSessionType.FP2,
    StageSessionType.FP3,
    StageSessionType.PRACTICE_COMPLETION,
)


def _practice_status(value: StageSessionStatus) -> PracticeSegmentStatus:
    return PracticeSegmentStatus(value.value)


def _stage_status(value: StageSessionStatus) -> StageStatus:
    if value == StageSessionStatus.COMPLETED:
        return StageStatus.COMPLETED
    if value == StageSessionStatus.AVAILABLE:
        return StageStatus.AVAILABLE
    return StageStatus.LOCKED
