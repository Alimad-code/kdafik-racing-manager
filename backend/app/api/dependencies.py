from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError, ErrorCode
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models import User
from app.repositories.auth import AuthRepository
from app.repositories.catalog import CatalogRepository
from app.repositories.season import SeasonRepository
from app.repositories.stage_session import StageSessionRepository
from app.services.auth import AuthService
from app.services.catalog import CatalogService
from app.services.email import EmailSender, SmtpEmailSender
from app.services.season import SeasonService
from app.services.stage_session import StageSessionService

DatabaseSession = Annotated[Session, Depends(get_db_session)]
bearer_scheme = HTTPBearer(auto_error=False)


def get_email_sender() -> EmailSender | None:
    settings = get_settings()
    return SmtpEmailSender(settings) if settings.email_enabled else None


def get_auth_service(
    session: DatabaseSession, email_sender: Annotated[EmailSender | None, Depends(get_email_sender)]
) -> AuthService:
    season_repository = SeasonRepository(session)
    return AuthService(
        AuthRepository(session),
        SeasonService(season_repository),
        get_settings(),
        email_sender,
    )


def get_current_user(
    session: DatabaseSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise DomainError(
            ErrorCode.UNAUTHORIZED,
            "Bearer access token is required.",
            status_code=401,
        )

    user_id: UUID = decode_access_token(credentials.credentials, get_settings())
    user = AuthRepository(session).get_user_by_id(user_id)
    if user is None:
        raise DomainError(
            ErrorCode.UNAUTHORIZED,
            "Authenticated user was not found.",
            status_code=401,
        )
    return user


def get_catalog_service(session: DatabaseSession) -> CatalogService:
    return CatalogService(CatalogRepository(session))


def get_season_service(session: DatabaseSession) -> SeasonService:
    return SeasonService(SeasonRepository(session))


def get_stage_session_service(session: DatabaseSession) -> StageSessionService:
    return StageSessionService(StageSessionRepository(session))


CatalogServiceDependency = Annotated[CatalogService, Depends(get_catalog_service)]
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDependency = Annotated[User, Depends(get_current_user)]
SeasonServiceDependency = Annotated[SeasonService, Depends(get_season_service)]
StageSessionServiceDependency = Annotated[
    StageSessionService,
    Depends(get_stage_session_service),
]
