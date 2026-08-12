from __future__ import annotations

from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError, ErrorCode
from app.models import LegalDocument, User, UserLegalAcceptance

REQUIRED_KINDS = ("privacy_policy", "personal_data_consent", "user_agreement")


def active_documents(session: Session, now: datetime | None = None) -> list[LegalDocument]:
    now = now or datetime.now(UTC)
    candidates = session.scalars(
        select(LegalDocument)
        .where(LegalDocument.retired_at.is_(None))
        .order_by(LegalDocument.kind, LegalDocument.effective_at.desc())
    ).all()
    return [item for item in candidates if _as_utc(item.effective_at) <= now]


def required_active_documents(session: Session) -> dict[str, LegalDocument]:
    documents = {
        item.kind: item for item in active_documents(session) if item.required_at_registration
    }
    if set(documents) != set(REQUIRED_KINDS):
        raise DomainError(
            ErrorCode.LEGAL_DOCUMENTS_UNAVAILABLE,
            "Required legal documents are temporarily unavailable.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return documents


def validate_acceptances(
    session: Session, entries, *, require_registration: bool
) -> list[LegalDocument]:
    active = (
        required_active_documents(session)
        if require_registration
        else {item.kind: item for item in active_documents(session)}
    )
    expected = set(REQUIRED_KINDS) if require_registration else set(active)
    received = [entry.kind for entry in entries]
    if len(received) != len(set(received)) or set(received) != expected:
        _invalid_acceptance("Each required legal document must be accepted exactly once.")
    documents: list[LegalDocument] = []
    for entry in entries:
        document = active.get(entry.kind)
        if document is None or document.version != entry.version or not entry.accepted:
            _invalid_acceptance("Acceptance does not match the current legal document.")
        documents.append(document)
    return documents


def accept_current_documents(session: Session, user: User, entries) -> list[UserLegalAcceptance]:
    documents = validate_acceptances(session, entries, require_registration=False)
    existing = {
        item.legal_document_id: item
        for item in session.scalars(
            select(UserLegalAcceptance).where(UserLegalAcceptance.user_id == user.id)
        )
    }
    now = datetime.now(UTC)
    created: list[UserLegalAcceptance] = []
    for document in documents:
        if document.id not in existing:
            acceptance = UserLegalAcceptance(
                user_id=user.id,
                legal_document_id=document.id,
                accepted_at=now,
                source="account",
            )
            session.add(acceptance)
            created.append(acceptance)
    session.commit()
    return created


def acceptance_status(session: Session, user: User) -> list[dict]:
    documents = active_documents(session)
    accepted_ids = set(
        session.scalars(
            select(UserLegalAcceptance.legal_document_id).where(
                UserLegalAcceptance.user_id == user.id
            )
        )
    )
    return [{"document": item, "accepted": item.id in accepted_ids} for item in documents]


def _invalid_acceptance(message: str) -> None:
    raise DomainError(
        ErrorCode.INVALID_LEGAL_ACCEPTANCE,
        message,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
