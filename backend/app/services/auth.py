from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import status

from app.core.config import Settings
from app.core.errors import DomainError, ErrorCode
from app.core.security import (
    create_access_token,
    generate_email_code,
    generate_refresh_token,
    hash_email_code,
    hash_password,
    hash_refresh_token,
    verify_email_code,
    verify_password,
)
from app.domain.enums import UserRole
from app.models import (
    EmailActionCode,
    PendingRegistration,
    PendingRegistrationAcceptance,
    User,
    UserLegalAcceptance,
    UserSession,
    WebSocketTicket,
)
from app.repositories.auth import AuthRepository
from app.schemas.auth import (
    AuthSessionRead,
    ChangePasswordRequest,
    DeleteAccountRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    RegistrationConfirmationRequest,
    ResetPasswordRequest,
)
from app.schemas.season import SeasonCreate, UserRead
from app.services.email import EmailDeliveryError, EmailSender
from app.services.legal import validate_acceptances
from app.services.season import SeasonService


class AuthResult:
    def __init__(self, payload: AuthSessionRead, refresh_token: str) -> None:
        self.payload = payload
        self.refresh_token = refresh_token


PASSWORD_RESET = "password_reset"
REGISTRATION_TTL = timedelta(hours=24)
REGISTRATION_CODE_TTL = timedelta(minutes=15)
PASSWORD_RESET_CODE_TTL = timedelta(minutes=10)
EMAIL_CODE_RESEND_COOLDOWN = timedelta(seconds=60)


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        season_service: SeasonService,
        settings: Settings,
        email_sender: EmailSender | None = None,
    ) -> None:
        self.repository = repository
        self.season_service = season_service
        self.settings = settings
        self.email_sender = email_sender

    def register(self, payload: RegisterRequest) -> tuple[UUID, str]:
        try:
            email = self._normalize_email(payload.email)
            display_name = self._normalize_display_name(payload.display_name)
            display_name_normalized = self._normalize_display_name_for_lookup(display_name)
            if not payload.age_confirmed:
                raise DomainError(
                    ErrorCode.AGE_CONFIRMATION_REQUIRED,
                    "Account registration requires confirmation that the user is at least "
                    "18 years old.",
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                )
            if not display_name:
                raise DomainError(
                    ErrorCode.VALIDATION_ERROR,
                    "Display name is required.",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            if self.repository.get_user_by_email(email) is not None:
                raise DomainError(
                    ErrorCode.EMAIL_ALREADY_REGISTERED,
                    "Email is already registered.",
                    status_code=status.HTTP_409_CONFLICT,
                    details={"email": email},
                )
            if (
                self.repository.get_user_by_display_name_normalized(display_name_normalized)
                is not None
            ):
                raise DomainError(
                    ErrorCode.DISPLAY_NAME_ALREADY_REGISTERED,
                    "Display name is already registered.",
                    status_code=status.HTTP_409_CONFLICT,
                    details={"displayName": display_name},
                )

            self._require_email_sender()
            documents = validate_acceptances(
                self.repository.session, payload.legal_acceptances, require_registration=True
            )
            pending_by_email = self.repository.get_pending_registration_by_email(email)
            if pending_by_email is not None:
                if self._registration_can_resend(pending_by_email, datetime.now(UTC)):
                    self._send_registration_confirmation(pending_by_email)
                else:
                    self.repository.commit()
                return pending_by_email.id, self._mask_email(pending_by_email.email)
            if (
                self.repository.get_pending_registration_by_display_name_normalized(
                    display_name_normalized
                )
                is not None
            ):
                raise DomainError(
                    ErrorCode.DISPLAY_NAME_ALREADY_REGISTERED,
                    "Display name is already registered.",
                    status_code=status.HTTP_409_CONFLICT,
                    details={"displayName": display_name},
                )

            now = datetime.now(UTC)
            code = generate_email_code()
            registration_id = uuid4()
            registration = PendingRegistration(
                display_name=display_name,
                display_name_normalized=display_name_normalized,
                email=email,
                password_hash=hash_password(payload.password),
                age_confirmed=True,
                id=registration_id,
                confirmation_code_hash=hash_email_code(
                    self.settings, "registration", registration_id, code
                ),
                code_expires_at=now + REGISTRATION_CODE_TTL,
                expires_at=now + REGISTRATION_TTL,
                sent_at=now,
            )
            self.repository.add_pending_registration(registration)
            self.repository.flush()
            for document in documents:
                self.repository.session.add(
                    PendingRegistrationAcceptance(
                        registration_id=registration.id,
                        kind=document.kind,
                        version=document.version,
                        accepted=True,
                    )
                )
            self.repository.commit()
            self._deliver_registration_confirmation(registration, code)
            return registration.id, self._mask_email(registration.email)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def login(self, payload: LoginRequest) -> AuthResult:
        try:
            user = self._get_user_by_login(payload.login)
            if user is None or not verify_password(payload.password, user.password_hash):
                raise DomainError(
                    ErrorCode.INVALID_CREDENTIALS,
                    "Invalid login or password.",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            if user.email_verified_at is None:
                raise DomainError(
                    ErrorCode.EMAIL_NOT_VERIFIED,
                    "Email address must be verified before login.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            auth_result = self._issue_auth_result(user)
            self.repository.commit()
            self.repository.expire_all()
            return self._auth_result_for_user(user.id, auth_result.refresh_token)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def refresh(self, refresh_token: str | None) -> AuthResult:
        try:
            if not refresh_token:
                self._raise_invalid_refresh_token()
            user_id = self.repository.consume_refresh_session(
                hash_refresh_token(refresh_token), datetime.now(UTC)
            )
            if user_id is None:
                self._raise_invalid_refresh_token()
            user = self.repository.get_user_by_id(user_id)
            if user is None:
                self._raise_invalid_refresh_token()
            auth_result = self._issue_auth_result(user)
            self.repository.commit()
            self.repository.expire_all()
            return self._auth_result_for_user(user.id, auth_result.refresh_token)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def logout(self, refresh_token: str | None) -> None:
        try:
            if refresh_token:
                user_session = self.repository.get_refresh_session(
                    hash_refresh_token(refresh_token)
                )
                if user_session is not None and user_session.revoked_at is None:
                    self.repository.revoke_refresh_session(user_session, datetime.now(UTC))
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

    def update_profile(self, user: User, payload: ProfileUpdateRequest) -> User:
        try:
            display_name = self._normalize_display_name(payload.display_name)
            display_name_normalized = self._normalize_display_name_for_lookup(display_name)
            if not display_name:
                raise DomainError(
                    ErrorCode.VALIDATION_ERROR,
                    "Display name is required.",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            existing_user = self.repository.get_user_by_display_name_normalized(
                display_name_normalized
            )
            if existing_user is not None and existing_user.id != user.id:
                raise DomainError(
                    ErrorCode.DISPLAY_NAME_ALREADY_REGISTERED,
                    "Display name is already registered.",
                    status_code=status.HTTP_409_CONFLICT,
                    details={"displayName": display_name},
                )

            user.display_name = display_name
            user.display_name_normalized = display_name_normalized
            user_id = user.id
            self.repository.commit()
            self.repository.expire_all()
            updated_user = self.repository.get_user_by_id(user_id)
            if updated_user is None:
                raise DomainError(
                    ErrorCode.UNAUTHORIZED,
                    "Authenticated user was not found.",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            return updated_user
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        try:
            self._check_current_password(user, payload.current_password)
            if verify_password(payload.new_password, user.password_hash):
                raise DomainError(
                    ErrorCode.VALIDATION_ERROR,
                    "New password must be different from the current password.",
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    details={"field": "newPassword"},
                )
            user.password_hash = hash_password(payload.new_password)
            self.repository.revoke_all_refresh_sessions(user.id, datetime.now(UTC))
            self.repository.commit()
            self._notify_password_changed(user.email)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def delete_account(self, user: User, payload: DeleteAccountRequest) -> None:
        try:
            self._check_current_password(user, payload.current_password)
            user.active_season_id = None
            self.repository.flush()
            self.repository.delete_completed_registrations(user.id)
            self.repository.delete_user(user)
            self.repository.commit()
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def issue_websocket_ticket(self, user: User) -> tuple[str, int]:
        """Issue a one-time ticket. Only its SHA-256 digest is persisted."""
        try:
            now = datetime.now(UTC)
            self.repository.cleanup_expired_websocket_tickets(now)
            self.repository.invalidate_pending_websocket_tickets(user.id, now)
            ticket = generate_refresh_token()
            lifetime_seconds = 60
            self.repository.add_websocket_ticket(
                WebSocketTicket(
                    user_id=user.id,
                    ticket_hash=hash_refresh_token(ticket),
                    expires_at=now + timedelta(seconds=lifetime_seconds),
                )
            )
            self.repository.commit()
            return ticket, lifetime_seconds
        except Exception:
            self.repository.rollback()
            raise

    def resend_registration_confirmation(self, confirmation_id: UUID) -> None:
        self._require_email_sender()
        try:
            registration = self.repository.get_pending_registration_for_update_by_id(
                confirmation_id
            )
            now = datetime.now(UTC)
            if (
                registration is None
                or registration.confirmed_at is not None
                or self._as_utc(registration.expires_at) <= now
            ):
                self.repository.commit()
                return
            if not self._registration_can_resend(registration, now):
                self.repository.commit()
                return
            self._send_registration_confirmation(registration)
        except DomainError as exc:
            self.repository.rollback()
            if exc.code == ErrorCode.EMAIL_DELIVERY_UNAVAILABLE:
                return
            raise
        except Exception:
            self.repository.rollback()
            raise

    def confirm_registration(self, payload: RegistrationConfirmationRequest) -> None:
        try:
            now = datetime.now(UTC)
            registration = self.repository.get_pending_registration_for_update_by_id(
                payload.confirmation_id
            )
            if (
                registration is None
                or registration.confirmed_at is not None
                or self._as_utc(registration.expires_at) <= now
                or self._as_utc(registration.code_expires_at) <= now
                or registration.code_failed_attempts >= 5
                or not verify_email_code(
                    self.settings,
                    "registration",
                    registration.id,
                    payload.code,
                    registration.confirmation_code_hash,
                )
            ):
                if registration is not None and registration.confirmed_at is None:
                    registration_id = registration.id
                    self.repository.session.expire(registration)
                    self.repository.record_pending_registration_code_failure(registration_id, now)
                self.repository.commit()
                self._raise_invalid_email_action_code()
            if not registration.age_confirmed:
                raise DomainError(
                    ErrorCode.AGE_CONFIRMATION_REQUIRED,
                    "Account registration requires confirmation that the user is at least "
                    "18 years old.",
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                )
            accepted = {
                item.kind: item.version for item in registration.acceptances if item.accepted
            }
            current = validate_acceptances(
                self.repository.session,
                payload.legal_acceptances
                or [
                    type("Acceptance", (), {"kind": kind, "version": version, "accepted": True})
                    for kind, version in accepted.items()
                ],
                require_registration=True,
            )
            current_versions = {item.kind: item.version for item in current}
            if accepted != current_versions and payload.legal_acceptances is None:
                raise DomainError(
                    ErrorCode.INVALID_LEGAL_ACCEPTANCE,
                    "Current legal document acceptances are required.",
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                )
            user = User(
                display_name=registration.display_name,
                display_name_normalized=registration.display_name_normalized,
                email=registration.email,
                password_hash=registration.password_hash,
                role=UserRole.TEAM_PRINCIPAL,
                email_verified_at=now,
                age_confirmed_at=now if registration.age_confirmed else None,
            )
            self.repository.add_user(user)
            self.repository.flush()
            for document in current:
                self.repository.session.add(
                    UserLegalAcceptance(
                        user_id=user.id,
                        legal_document_id=document.id,
                        accepted_at=now,
                        source="registration",
                    )
                )
            season = self.season_service.create_initial_season_model(SeasonCreate(), user)
            user.active_season_id = season.id
            registration_id = registration.id
            self.repository.session.expire(registration)
            if not self.repository.consume_pending_registration_code(registration_id, now):
                self._raise_invalid_email_action_code()
            registration.completed_user_id = user.id
            user.email_verified_at = now
            self.repository.commit()
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def forgot_password(self, email: str) -> tuple[UUID, str]:
        self._require_email_sender()
        normalized_email = self._normalize_email(email)
        masked_email = self._mask_email(normalized_email)
        try:
            user = self.repository.get_user_by_email(normalized_email)
            if user is None:
                self.repository.commit()
                return uuid4(), masked_email
            now = datetime.now(UTC)
            current_code = self.repository.get_current_email_action_code_for_update(
                user.id, PASSWORD_RESET, now
            )
            if (
                current_code is not None
                and self._email_action_sent_at(current_code)
                >= now - EMAIL_CODE_RESEND_COOLDOWN
            ):
                self.repository.commit()
                return current_code.id, masked_email
            return self._send_new_email_action(user, PASSWORD_RESET), masked_email
        except DomainError as exc:
            self.repository.rollback()
            if exc.code == ErrorCode.EMAIL_DELIVERY_UNAVAILABLE:
                return uuid4(), masked_email
            raise
        except Exception:
            self.repository.rollback()
            raise

    def resend_password_reset(self, reset_id: UUID) -> None:
        self._require_email_sender()
        try:
            previous_code = self.repository.get_email_action_code_for_resend(reset_id)
            if (
                previous_code is None
                or previous_code.purpose != PASSWORD_RESET
                or previous_code.consumed_at is not None
            ):
                self.repository.commit()
                return
            user = self.repository.get_user_by_id(previous_code.user_id)
            if user is None:
                self.repository.commit()
                return
            now = datetime.now(UTC)
            current_code = self.repository.get_current_email_action_code_for_update(
                user.id, PASSWORD_RESET, now
            )
            if (
                current_code is not None
                and self._email_action_sent_at(current_code)
                >= now - EMAIL_CODE_RESEND_COOLDOWN
            ):
                self.repository.commit()
                return
            self._resend_email_action(previous_code, user, PASSWORD_RESET)
        except DomainError as exc:
            self.repository.rollback()
            if exc.code == ErrorCode.EMAIL_DELIVERY_UNAVAILABLE:
                return
            raise
        except Exception:
            self.repository.rollback()
            raise

    def reset_password(self, payload: ResetPasswordRequest) -> None:
        try:
            now = datetime.now(UTC)
            code = self.repository.get_email_action_code_for_update_by_id(
                payload.reset_id, PASSWORD_RESET, now
            )
            user = self.repository.get_user_by_id(code.user_id) if code is not None else None
            if (
                user is None
                or code is None
                or not verify_email_code(
                    self.settings, PASSWORD_RESET, user.id, payload.code, code.code_hash
                )
            ):
                if code is not None:
                    code_id = code.id
                    self.repository.session.expire(code)
                    self.repository.record_email_action_code_failure(code_id, now)
                self.repository.commit()
                self._raise_invalid_email_action_code()
            code_id = code.id
            self.repository.session.expire(code)
            if self.repository.consume_email_action_code(code_id, now) is None:
                self._raise_invalid_email_action_code()
            user.password_hash = hash_password(payload.new_password)
            self.repository.revoke_all_refresh_sessions(user.id, now)
            self.repository.invalidate_pending_websocket_tickets(user.id, now)
            self.repository.commit()
            self._notify_password_changed(user.email)
        except DomainError:
            self.repository.rollback()
            raise
        except Exception:
            self.repository.rollback()
            raise

    def _send_new_email_action(self, user: User, purpose: str) -> UUID:
        """Persist only a context-bound code digest; the code exists only for delivery."""
        now = datetime.now(UTC)
        code = generate_email_code()
        self.repository.invalidate_pending_email_codes(user.id, purpose, now)
        action_code = EmailActionCode(
            user_id=user.id,
            purpose=purpose,
            code_hash=hash_email_code(self.settings, purpose, user.id, code),
            expires_at=now + PASSWORD_RESET_CODE_TTL,
        )
        self.repository.add_email_action_code(action_code)
        self.repository.commit()
        try:
            self.email_sender.send_password_reset(user.email, code)  # type: ignore[union-attr]
        except EmailDeliveryError:
            action_code.expires_at = datetime.now(UTC)
            self.repository.commit()
        return action_code.id

    def _resend_email_action(
        self, action_code: EmailActionCode, user: User, purpose: str
    ) -> None:
        now = datetime.now(UTC)
        code = generate_email_code()
        action_code.code_hash = hash_email_code(self.settings, purpose, user.id, code)
        action_code.expires_at = now + PASSWORD_RESET_CODE_TTL
        action_code.failed_attempts = 0
        action_code.consumed_at = None
        self.repository.commit()
        try:
            self.email_sender.send_password_reset(user.email, code)  # type: ignore[union-attr]
        except EmailDeliveryError:
            action_code.expires_at = datetime.now(UTC)
            self.repository.commit()

    def _email_action_sent_at(self, action_code: EmailActionCode) -> datetime:
        return max(
            self._as_utc(action_code.created_at),
            self._as_utc(action_code.updated_at),
        )

    @staticmethod
    def _registration_can_resend(registration: PendingRegistration, now: datetime) -> bool:
        sent_at = registration.sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=UTC)
        return sent_at <= now - EMAIL_CODE_RESEND_COOLDOWN

    def _send_registration_confirmation(self, registration: PendingRegistration) -> None:
        code = generate_email_code()
        now = datetime.now(UTC)
        registration.confirmation_code_hash = hash_email_code(
            self.settings, "registration", registration.id, code
        )
        registration.code_expires_at = now + REGISTRATION_CODE_TTL
        registration.code_failed_attempts = 0
        registration.sent_at = now
        self.repository.commit()
        self._deliver_registration_confirmation(registration, code)

    def _deliver_registration_confirmation(
        self, registration: PendingRegistration, code: str
    ) -> None:
        try:
            self.email_sender.send_verification(registration.email, code)  # type: ignore[union-attr]
        except EmailDeliveryError:
            registration.code_expires_at = datetime.now(UTC)
            registration.sent_at = datetime.now(UTC) - EMAIL_CODE_RESEND_COOLDOWN
            self.repository.commit()
            raise DomainError(
                ErrorCode.EMAIL_DELIVERY_UNAVAILABLE,
                "Email delivery is temporarily unavailable.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from None

    def _require_email_sender(self) -> None:
        if self.email_sender is None:
            raise DomainError(
                ErrorCode.EMAIL_DELIVERY_UNAVAILABLE,
                "Email delivery is temporarily unavailable.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    @staticmethod
    def _mask_email(email: str) -> str:
        local_part, separator, domain = email.partition("@")
        if not separator:
            return email
        visible = local_part[:2]
        return f"{visible}{'*' * max(1, len(local_part) - len(visible))}@{domain}"

    def _notify_password_changed(self, recipient: str) -> None:
        if self.email_sender is None:
            return
        try:
            self.email_sender.send_password_changed(recipient)
        except EmailDeliveryError:
            return

    def _valid_refresh_session(self, refresh_token: str | None) -> UserSession:
        if not refresh_token:
            self._raise_invalid_refresh_token()

        user_session = self.repository.get_refresh_session(hash_refresh_token(refresh_token))
        now = datetime.now(UTC)
        expires_at = self._as_utc(user_session.expires_at) if user_session is not None else None
        if user_session is None or user_session.revoked_at is not None or expires_at <= now:
            self._raise_invalid_refresh_token()
        return user_session

    def _issue_auth_result(self, user: User) -> AuthResult:
        refresh_token = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_days)
        self.repository.add_refresh_session(
            UserSession(
                user_id=user.id,
                refresh_token_hash=hash_refresh_token(refresh_token),
                expires_at=expires_at,
            )
        )
        self.repository.flush()
        return AuthResult(self._build_payload(user), refresh_token)

    def _auth_result_for_user(self, user_id, refresh_token: str) -> AuthResult:
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise DomainError(
                ErrorCode.UNAUTHORIZED,
                "Authenticated user was not found.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        return AuthResult(self._build_payload(user), refresh_token)

    def _build_payload(self, user: User) -> AuthSessionRead:
        access_token, expires_in = create_access_token(user.id, self.settings)
        active_season = (
            self.season_service.get_season(user.active_season_id, user)
            if user.active_season_id is not None
            else None
        )
        return AuthSessionRead(
            access_token=access_token,
            expires_in_seconds=expires_in,
            user=UserRead.model_validate(user),
            active_season_id=user.active_season_id,
            active_season=active_season,
        )

    def _get_user_by_login(self, login: str) -> User | None:
        normalized_login = login.strip()
        if not normalized_login:
            return None

        user = self.repository.get_user_by_email(self._normalize_email(normalized_login))
        if user is not None:
            return user

        return self.repository.get_user_by_display_name_normalized(
            self._normalize_display_name_for_lookup(normalized_login)
        )

    @staticmethod
    def _check_current_password(user: User, password: str) -> None:
        if not verify_password(password, user.password_hash):
            raise DomainError(
                ErrorCode.INVALID_CREDENTIALS,
                "Invalid login or password.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _normalize_display_name(display_name: str) -> str:
        return display_name.strip()

    @staticmethod
    def _normalize_display_name_for_lookup(display_name: str) -> str:
        return display_name.strip().casefold()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _raise_invalid_refresh_token() -> None:
        raise DomainError(
            ErrorCode.INVALID_TOKEN,
            "Invalid or expired refresh token.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    @staticmethod
    def _raise_invalid_email_action_code() -> None:
        raise DomainError(
            ErrorCode.INVALID_EMAIL_ACTION_CODE,
            "Invalid or expired email action code.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
