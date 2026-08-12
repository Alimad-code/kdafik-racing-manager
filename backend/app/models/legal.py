from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


DOCUMENT_KINDS = ("privacy_policy", "personal_data_consent", "user_agreement")
ACCEPTANCE_SOURCES = ("registration", "account")


class LegalDocument(TimestampMixin, Base):
    """Metadata of a published legal text. The text itself is deliberately not stored here."""

    __tablename__ = "legal_documents"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('privacy_policy', 'personal_data_consent', 'user_agreement')",
            name="ck_legal_documents_kind",
        ),
        CheckConstraint("length(content_sha256) = 64", name="ck_legal_documents_sha256_length"),
        Index("uq_legal_documents_kind_version", "kind", "version", unique=True),
        # PostgreSQL enforces this. Service validation supplies the equivalent guard on SQLite.
        Index(
            "uq_legal_documents_one_active_kind",
            "kind",
            unique=True,
            postgresql_where=text("retired_at IS NULL"),
            sqlite_where=text("retired_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    public_path: Mapped[str] = mapped_column(String(512), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    required_at_registration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    acceptances: Mapped[list[UserLegalAcceptance]] = relationship(back_populates="legal_document")


class UserLegalAcceptance(TimestampMixin, Base):
    __tablename__ = "user_legal_acceptances"
    __table_args__ = (
        CheckConstraint(
            "source IN ('registration', 'account')", name="ck_user_legal_acceptances_source"
        ),
        Index(
            "uq_user_legal_acceptances_user_document",
            "user_id",
            "legal_document_id",
            unique=True,
        ),
        Index("ix_user_legal_acceptances_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    legal_document_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("legal_documents.id", ondelete="RESTRICT"), nullable=False
    )
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    user: Mapped[User] = relationship(back_populates="legal_acceptances")
    legal_document: Mapped[LegalDocument] = relationship(back_populates="acceptances")
