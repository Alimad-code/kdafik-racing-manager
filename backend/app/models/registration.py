from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PendingRegistration(TimestampMixin, Base):
    """Registration data held until an email token is explicitly confirmed."""

    __tablename__ = "pending_registrations"
    __table_args__ = (
        Index("ix_pending_registrations_token_hash", "confirmation_token_hash", unique=True),
        Index("ix_pending_registrations_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name_normalized: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    confirmation_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

    acceptances: Mapped[list[PendingRegistrationAcceptance]] = relationship(
        back_populates="registration", cascade="all, delete-orphan"
    )


class PendingRegistrationAcceptance(Base):
    __tablename__ = "pending_registration_acceptances"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('privacy_policy', 'personal_data_consent', 'user_agreement')",
            name="ck_pending_registration_acceptances_kind",
        ),
        UniqueConstraint(
            "registration_id",
            "kind",
            name="uq_pending_registration_acceptances_registration_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    registration_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("pending_registrations.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)

    registration: Mapped[PendingRegistration] = relationship(back_populates="acceptances")
