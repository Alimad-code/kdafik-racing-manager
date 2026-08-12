from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.dependencies import AuthServiceDependency, CurrentUserDependency
from app.core.config import get_settings
from app.schemas.auth import (
    AcceptedResponse,
    AuthSessionRead,
    ChangePasswordRequest,
    DeleteAccountRequest,
    EmailRequest,
    LoginRequest,
    ProfileRead,
    ProfileUpdateRequest,
    RegisterRequest,
    RegistrationConfirmationRequest,
    ResetPasswordRequest,
)
from app.schemas.season import UserRead
from app.services.user_data import build_user_export

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AcceptedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a pending registration",
)
def register(
    payload: RegisterRequest,
    service: AuthServiceDependency,
) -> AcceptedResponse:
    service.register(payload)
    return AcceptedResponse()


@router.post("/registration/resend", response_model=AcceptedResponse)
def resend_registration_confirmation(
    payload: EmailRequest, service: AuthServiceDependency
) -> AcceptedResponse:
    service.resend_registration_confirmation(payload.email)
    return AcceptedResponse()


@router.post("/registration/confirm", response_model=AcceptedResponse)
def confirm_registration(
    payload: RegistrationConfirmationRequest, service: AuthServiceDependency
) -> AcceptedResponse:
    service.confirm_registration(payload)
    return AcceptedResponse()


@router.post("/password/forgot", response_model=AcceptedResponse)
def forgot_password(payload: EmailRequest, service: AuthServiceDependency) -> AcceptedResponse:
    service.forgot_password(payload.email)
    return AcceptedResponse()


@router.post("/password/reset", response_model=AcceptedResponse)
def reset_password(
    payload: ResetPasswordRequest, service: AuthServiceDependency
) -> AcceptedResponse:
    service.reset_password(payload)
    return AcceptedResponse()


@router.post("/login", response_model=AuthSessionRead, summary="Log in user")
def login(
    payload: LoginRequest,
    response: Response,
    service: AuthServiceDependency,
) -> AuthSessionRead:
    result = service.login(payload)
    set_refresh_cookie(response, result.refresh_token)
    return result.payload


@router.post("/refresh", response_model=AuthSessionRead, summary="Refresh access token")
def refresh(
    request: Request, response: Response, service: AuthServiceDependency
) -> AuthSessionRead:
    settings = get_settings()
    require_same_origin_for_cookie_auth(request, settings)
    result = service.refresh(request.cookies.get(settings.refresh_cookie_name))
    set_refresh_cookie(response, result.refresh_token)
    return result.payload


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Log out current session")
def logout(request: Request, response: Response, service: AuthServiceDependency) -> None:
    settings = get_settings()
    require_same_origin_for_cookie_auth(request, settings)
    service.logout(request.cookies.get(settings.refresh_cookie_name))
    clear_refresh_cookie(response)


@router.get("/me", response_model=UserRead, summary="Get current user")
def me(user: CurrentUserDependency) -> UserRead:
    return UserRead.model_validate(user)


@router.get("/me/export", summary="Download current user data")
def export_me(user: CurrentUserDependency, service: AuthServiceDependency) -> JSONResponse:
    export = build_user_export(service.repository.session, user.id)
    return JSONResponse(
        export,
        headers={
            "Content-Disposition": 'attachment; filename="kdafik-racing-manager-data.json"',
        },
    )


@router.patch("/me", response_model=UserRead, summary="Update current user")
def update_me(
    payload: ProfileUpdateRequest,
    user: CurrentUserDependency,
    service: AuthServiceDependency,
) -> UserRead:
    return UserRead.model_validate(service.update_profile(user, payload))


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change current user password",
)
def change_password(
    payload: ChangePasswordRequest,
    user: CurrentUserDependency,
    service: AuthServiceDependency,
) -> None:
    service.change_password(user, payload)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete current user")
def delete_me(
    payload: DeleteAccountRequest,
    response: Response,
    user: CurrentUserDependency,
    service: AuthServiceDependency,
) -> None:
    service.delete_account(user, payload)
    clear_refresh_cookie(response)


@router.get("/profile", response_model=ProfileRead, summary="Get current user profile")
def profile(user: CurrentUserDependency) -> ProfileRead:
    return ProfileRead.model_validate(user)


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path=f"{settings.api_v1_prefix}/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path=f"{settings.api_v1_prefix}/auth",
    )


def require_same_origin_for_cookie_auth(request: Request, settings) -> None:
    """Cookie-auth endpoints require an allowed browser Origin in production.

    Local and test clients without an Origin remain supported for API tooling; production
    browser requests must originate from one of the explicit CORS origins.
    """
    origin = request.headers.get("origin")
    if settings.environment == "production":
        if origin not in settings.cors_origins:
            from app.core.errors import DomainError, ErrorCode

            raise DomainError(ErrorCode.UNAUTHORIZED, "Invalid request origin.", status_code=403)
    elif origin is not None and origin not in settings.cors_origins:
        from app.core.errors import DomainError, ErrorCode

        raise DomainError(ErrorCode.UNAUTHORIZED, "Invalid request origin.", status_code=403)
