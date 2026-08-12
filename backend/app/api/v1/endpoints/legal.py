from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import CurrentUserDependency, DatabaseSession
from app.core.config import get_settings
from app.schemas.auth import (
    LegalAcceptanceRequest,
    LegalAcceptanceStatusRead,
    LegalDocumentContentRead,
    LegalDocumentRead,
)
from app.services.legal import accept_current_documents, acceptance_status, active_documents
from app.services.legal_manifest import get_runtime_document

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/documents/active", response_model=list[LegalDocumentRead])
def get_active_documents(session: DatabaseSession, response: Response) -> list[LegalDocumentRead]:
    response.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
    return [LegalDocumentRead.model_validate(item) for item in active_documents(session)]


@router.get("/documents/{kind}", response_model=LegalDocumentContentRead)
def get_public_document(kind: str, response: Response) -> LegalDocumentContentRead:
    try:
        document = get_runtime_document(kind, environment=get_settings().environment)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Legal document is unavailable.",
        ) from exc
    response.headers["Cache-Control"] = "no-store"
    return LegalDocumentContentRead.model_validate(document)


@router.get("/acceptances/me", response_model=list[LegalAcceptanceStatusRead])
def get_my_acceptances(
    user: CurrentUserDependency, session: DatabaseSession
) -> list[LegalAcceptanceStatusRead]:
    return [
        LegalAcceptanceStatusRead(document=item["document"], accepted=item["accepted"])
        for item in acceptance_status(session, user)
    ]


@router.post("/acceptances", status_code=status.HTTP_204_NO_CONTENT)
def accept_documents(
    payload: list[LegalAcceptanceRequest], user: CurrentUserDependency, session: DatabaseSession
) -> None:
    accept_current_documents(session, user, payload)
