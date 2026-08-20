from datetime import datetime
from uuid import UUID

from sqlalchemy import case, delete, select, update
from sqlalchemy.orm import Session, selectinload

from app.models import EmailActionCode, PendingRegistration, User, UserSession, WebSocketTicket

MAX_EMAIL_CODE_FAILED_ATTEMPTS = 5


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.session.scalar(statement)

    def get_user_by_display_name_normalized(self, display_name_normalized: str) -> User | None:
        statement = select(User).where(User.display_name_normalized == display_name_normalized)
        return self.session.scalar(statement)

    def get_user_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_pending_registration_by_email(self, email: str) -> PendingRegistration | None:
        return self.session.scalar(
            select(PendingRegistration).where(PendingRegistration.email == email)
        )

    def get_pending_registration_by_display_name_normalized(
        self, display_name_normalized: str
    ) -> PendingRegistration | None:
        return self.session.scalar(
            select(PendingRegistration).where(
                PendingRegistration.display_name_normalized == display_name_normalized
            )
        )

    def get_pending_registration_for_update_by_id(
        self, registration_id: UUID
    ) -> PendingRegistration | None:
        return self.session.scalar(
            select(PendingRegistration).where(
                PendingRegistration.id == registration_id
            ).with_for_update()
        )

    def consume_pending_registration_code(self, registration_id: UUID, now: datetime) -> bool:
        statement = (
            update(PendingRegistration)
            .where(
                PendingRegistration.id == registration_id,
                PendingRegistration.confirmed_at.is_(None),
                PendingRegistration.code_expires_at > now,
                PendingRegistration.code_failed_attempts < MAX_EMAIL_CODE_FAILED_ATTEMPTS,
            )
            .values(confirmed_at=now)
            .returning(PendingRegistration.id)
        )
        return self.session.scalar(statement) is not None

    def record_pending_registration_code_failure(
        self, registration_id: UUID, now: datetime
    ) -> bool:
        attempts = PendingRegistration.code_failed_attempts + 1
        statement = (
            update(PendingRegistration)
            .where(
                PendingRegistration.id == registration_id,
                PendingRegistration.confirmed_at.is_(None),
                PendingRegistration.code_expires_at > now,
                PendingRegistration.code_failed_attempts < MAX_EMAIL_CODE_FAILED_ATTEMPTS,
            )
            .values(
                code_failed_attempts=attempts,
                code_expires_at=case(
                    (attempts >= MAX_EMAIL_CODE_FAILED_ATTEMPTS, now),
                    else_=PendingRegistration.code_expires_at,
                ),
            )
            .returning(PendingRegistration.code_failed_attempts)
        )
        return self.session.scalar(statement) is not None

    def add_pending_registration(self, registration: PendingRegistration) -> None:
        self.session.add(registration)

    def get_refresh_session(self, refresh_token_hash: str) -> UserSession | None:
        statement = (
            select(UserSession)
            .where(UserSession.refresh_token_hash == refresh_token_hash)
            .options(selectinload(UserSession.user))
        )
        return self.session.scalar(statement)

    def add_user(self, user: User) -> None:
        self.session.add(user)

    def add_refresh_session(self, user_session: UserSession) -> None:
        self.session.add(user_session)

    def delete_user(self, user: User) -> None:
        self.session.delete(user)

    def delete_completed_registrations(self, user_id: UUID) -> None:
        registrations = self.session.scalars(
            select(PendingRegistration).where(PendingRegistration.completed_user_id == user_id)
        ).all()
        for registration in registrations:
            self.session.delete(registration)

    def revoke_refresh_session(self, user_session: UserSession, revoked_at: datetime) -> None:
        user_session.revoked_at = revoked_at

    def consume_refresh_session(self, refresh_token_hash: str, now: datetime) -> UUID | None:
        statement = (
            update(UserSession)
            .where(
                UserSession.refresh_token_hash == refresh_token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .values(revoked_at=now)
            .returning(UserSession.user_id)
        )
        return self.session.scalar(statement)

    def revoke_all_refresh_sessions(self, user_id: UUID, revoked_at: datetime) -> None:
        self.session.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )

    def add_websocket_ticket(self, ticket: WebSocketTicket) -> None:
        self.session.add(ticket)

    def add_email_action_code(self, code: EmailActionCode) -> None:
        self.session.add(code)

    def invalidate_pending_email_codes(self, user_id: UUID, purpose: str, now: datetime) -> None:
        self.session.execute(
            update(EmailActionCode)
            .where(
                EmailActionCode.user_id == user_id,
                EmailActionCode.purpose == purpose,
                EmailActionCode.consumed_at.is_(None),
                EmailActionCode.expires_at > now,
            )
            .values(consumed_at=now)
            .execution_options(synchronize_session=False)
        )

    def has_email_code_cooldown(
        self, user_id: UUID, purpose: str, cutoff: datetime, now: datetime
    ) -> bool:
        statement = select(EmailActionCode.id).where(
            EmailActionCode.user_id == user_id,
            EmailActionCode.purpose == purpose,
            EmailActionCode.created_at >= cutoff,
            EmailActionCode.consumed_at.is_(None),
            EmailActionCode.expires_at > now,
        )
        return self.session.scalar(statement) is not None

    def get_current_email_action_code_for_update(
        self, user_id: UUID, purpose: str, now: datetime
    ) -> EmailActionCode | None:
        statement = (
            select(EmailActionCode)
            .where(
                EmailActionCode.user_id == user_id,
                EmailActionCode.purpose == purpose,
                EmailActionCode.consumed_at.is_(None),
                EmailActionCode.expires_at > now,
                EmailActionCode.failed_attempts < MAX_EMAIL_CODE_FAILED_ATTEMPTS,
            )
            .order_by(EmailActionCode.created_at.desc())
            .with_for_update()
        )
        return self.session.scalar(statement)

    def get_email_action_code_for_update_by_id(
        self, code_id: UUID, purpose: str, now: datetime
    ) -> EmailActionCode | None:
        statement = (
            select(EmailActionCode)
            .where(
                EmailActionCode.id == code_id,
                EmailActionCode.purpose == purpose,
                EmailActionCode.consumed_at.is_(None),
                EmailActionCode.expires_at > now,
                EmailActionCode.failed_attempts < MAX_EMAIL_CODE_FAILED_ATTEMPTS,
            )
            .with_for_update()
        )
        return self.session.scalar(statement)

    def get_email_action_code_for_resend(self, code_id: UUID) -> EmailActionCode | None:
        return self.session.scalar(
            select(EmailActionCode).where(EmailActionCode.id == code_id).with_for_update()
        )

    def consume_email_action_code(self, code_id: UUID, now: datetime) -> UUID | None:
        statement = (
            update(EmailActionCode)
            .where(
                EmailActionCode.id == code_id,
                EmailActionCode.consumed_at.is_(None),
                EmailActionCode.expires_at > now,
                EmailActionCode.failed_attempts < MAX_EMAIL_CODE_FAILED_ATTEMPTS,
            )
            .values(consumed_at=now)
            .returning(EmailActionCode.user_id)
        )
        return self.session.scalar(statement)

    def record_email_action_code_failure(self, code_id: UUID, now: datetime) -> bool:
        attempts = EmailActionCode.failed_attempts + 1
        statement = (
            update(EmailActionCode)
            .where(
                EmailActionCode.id == code_id,
                EmailActionCode.consumed_at.is_(None),
                EmailActionCode.expires_at > now,
                EmailActionCode.failed_attempts < MAX_EMAIL_CODE_FAILED_ATTEMPTS,
            )
            .values(
                failed_attempts=attempts,
                consumed_at=case(
                    (attempts >= MAX_EMAIL_CODE_FAILED_ATTEMPTS, now),
                    else_=EmailActionCode.consumed_at,
                ),
            )
            .returning(EmailActionCode.failed_attempts)
        )
        return self.session.scalar(statement) is not None

    def invalidate_pending_websocket_tickets(self, user_id: UUID, now: datetime) -> None:
        self.session.execute(
            delete(WebSocketTicket).where(
                WebSocketTicket.user_id == user_id,
                WebSocketTicket.consumed_at.is_(None),
                WebSocketTicket.expires_at > now,
            )
        )

    def consume_websocket_ticket(self, ticket_hash: str, now: datetime) -> UUID | None:
        statement = (
            update(WebSocketTicket)
            .where(
                WebSocketTicket.ticket_hash == ticket_hash,
                WebSocketTicket.consumed_at.is_(None),
                WebSocketTicket.expires_at > now,
            )
            .values(consumed_at=now)
            .returning(WebSocketTicket.user_id)
        )
        return self.session.scalar(statement)

    def cleanup_expired_websocket_tickets(self, now: datetime, limit: int = 100) -> None:
        ids = self.session.scalars(
            select(WebSocketTicket.id)
            .where(WebSocketTicket.expires_at <= now)
            .order_by(WebSocketTicket.expires_at)
            .limit(limit)
        ).all()
        if ids:
            self.session.execute(delete(WebSocketTicket).where(WebSocketTicket.id.in_(ids)))

    def flush(self) -> None:
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def expire_all(self) -> None:
        self.session.expire_all()
