from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.catalog import to_camel
from app.schemas.season import SeasonRead, UserRead


class AuthSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )


class RegisterRequest(AuthSchema):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    age_confirmed: bool
    legal_acceptances: list["LegalAcceptanceRequest"] = Field(min_length=3, max_length=3)


class LegalAcceptanceRequest(AuthSchema):
    kind: str = Field(pattern=r"^(privacy_policy|personal_data_consent|user_agreement)$")
    version: str = Field(min_length=1, max_length=64)
    accepted: bool


class LegalDocumentRead(AuthSchema):
    kind: str
    version: str
    title: str
    public_path: str
    content_sha256: str
    effective_at: datetime
    required_at_registration: bool


class LegalDocumentContentRead(AuthSchema):
    kind: str
    version: str
    title: str
    public_path: str
    content_sha256: str
    effective_at: datetime
    is_draft: bool
    content: str


class LegalAcceptanceStatusRead(AuthSchema):
    document: LegalDocumentRead
    accepted: bool


class AcceptedResponse(AuthSchema):
    accepted: bool = True


class RegistrationChallengeRead(AcceptedResponse):
    confirmation_id: UUID
    masked_email: str


class PasswordResetChallengeRead(AcceptedResponse):
    reset_id: UUID
    masked_email: str


class EmailRequest(AuthSchema):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegistrationResendRequest(AuthSchema):
    confirmation_id: UUID


class RegistrationConfirmationRequest(AuthSchema):
    confirmation_id: UUID
    code: str = Field(pattern=r"^\d{6}$")
    legal_acceptances: list["LegalAcceptanceRequest"] | None = Field(
        default=None, min_length=3, max_length=3
    )


class PasswordResetResendRequest(AuthSchema):
    reset_id: UUID


class ResetPasswordRequest(AuthSchema):
    reset_id: UUID
    code: str = Field(pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=128)


class ProfileUpdateRequest(AuthSchema):
    display_name: str = Field(min_length=1, max_length=120)


class ChangePasswordRequest(AuthSchema):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountRequest(AuthSchema):
    current_password: str = Field(min_length=1, max_length=128)


class ProfileRead(UserRead):
    created_at: datetime
    updated_at: datetime


class LoginRequest(AuthSchema):
    login: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_email_login(cls, data):
        if isinstance(data, dict) and "login" not in data and "email" in data:
            return {**data, "login": data["email"]}
        return data


class AuthTokenRead(AuthSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class AuthSessionRead(AuthTokenRead):
    user: UserRead
    active_season_id: UUID | None
    active_season: SeasonRead | None = None


class WebSocketTicketRead(AuthSchema):
    ticket: str
    expires_in_seconds: int
