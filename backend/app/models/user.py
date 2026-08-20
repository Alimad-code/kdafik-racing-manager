from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import UserRole
from app.models.mixins import TimestampMixin
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.legal import UserLegalAcceptance
    from app.models.season import Season


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    display_name: Mapped[str] = mapped_column(String(120))
    display_name_normalized: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        enum_type(UserRole, "user_role", 32),
        default=UserRole.TEAM_PRINCIPAL,
    )
    active_season_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "seasons.id",
            name="fk_users_active_season_id",
            use_alter=True,
            ondelete="SET NULL",
        ),
    )

    seasons: Mapped[list[Season]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Season.user_id",
    )
    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    websocket_tickets: Mapped[list[WebSocketTicket]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    email_action_codes: Mapped[list[EmailActionCode]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    legal_acceptances: Mapped[list[UserLegalAcceptance]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    active_season: Mapped[Season | None] = relationship(
        foreign_keys=[active_season_id],
        post_update=True,
    )


class UserSession(TimestampMixin, Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_refresh_token_hash", "refresh_token_hash", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class WebSocketTicket(TimestampMixin, Base):
    __tablename__ = "websocket_tickets"
    __table_args__ = (
        Index("ix_websocket_tickets_ticket_hash", "ticket_hash", unique=True),
        Index("ix_websocket_tickets_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ticket_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="websocket_tickets")


class EmailActionCode(TimestampMixin, Base):
    __tablename__ = "email_action_codes"
    __table_args__ = (
        CheckConstraint(
            "purpose = 'password_reset'",
            name="ck_email_action_codes_purpose",
        ),
        CheckConstraint("failed_attempts >= 0", name="ck_email_action_codes_failed_attempts"),
        Index("ix_email_action_codes_code_hash", "code_hash", unique=True),
        Index("ix_email_action_codes_user_purpose", "user_id", "purpose"),
        Index("ix_email_action_codes_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    failed_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="email_action_codes")
