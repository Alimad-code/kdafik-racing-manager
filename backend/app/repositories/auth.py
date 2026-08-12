from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload

from app.models import EmailActionToken, PendingRegistration, User, UserSession, WebSocketTicket


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

    def get_pending_registration_by_token_hash(self, token_hash: str) -> PendingRegistration | None:
        return self.session.scalar(
            select(PendingRegistration).where(
                PendingRegistration.confirmation_token_hash == token_hash
            )
        )

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

    def add_email_action_token(self, token: EmailActionToken) -> None:
        self.session.add(token)

    def invalidate_pending_email_actions(self, user_id: UUID, purpose: str, now: datetime) -> None:
        self.session.execute(
            update(EmailActionToken)
            .where(
                EmailActionToken.user_id == user_id,
                EmailActionToken.purpose == purpose,
                EmailActionToken.consumed_at.is_(None),
                EmailActionToken.expires_at > now,
            )
            .values(consumed_at=now)
        )

    def has_email_action_cooldown(
        self, user_id: UUID, purpose: str, cutoff: datetime, now: datetime
    ) -> bool:
        statement = select(EmailActionToken.id).where(
            EmailActionToken.user_id == user_id,
            EmailActionToken.purpose == purpose,
            EmailActionToken.created_at >= cutoff,
            EmailActionToken.consumed_at.is_(None),
            EmailActionToken.expires_at > now,
        )
        return self.session.scalar(statement) is not None

    def consume_email_action(self, token_hash: str, purpose: str, now: datetime) -> UUID | None:
        statement = (
            update(EmailActionToken)
            .where(
                EmailActionToken.token_hash == token_hash,
                EmailActionToken.purpose == purpose,
                EmailActionToken.consumed_at.is_(None),
                EmailActionToken.expires_at > now,
            )
            .values(consumed_at=now)
            .returning(EmailActionToken.user_id)
        )
        return self.session.scalar(statement)

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
