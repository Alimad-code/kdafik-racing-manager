from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings
from app.core.errors import DomainError, ErrorCode

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
JWT_REQUIRED_CLAIMS = ["exp", "iat", "sub", "iss", "aud", "type"]
REFRESH_TOKEN_BYTES = 48

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def create_access_token(user_id: UUID, settings: Settings) -> tuple[str, int]:
    expires_delta = timedelta(minutes=settings.access_token_minutes)
    expires_at = datetime.now(UTC) + expires_delta
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": datetime.now(UTC),
        "exp": expires_at,
        "jti": str(uuid4()),
        "iss": settings.auth_jwt_issuer,
        "aud": settings.auth_jwt_audience,
    }
    token = jwt.encode(payload, settings.auth_jwt_secret, algorithm=ALGORITHM)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=[ALGORITHM],
            audience=settings.auth_jwt_audience,
            issuer=settings.auth_jwt_issuer,
            options={"require": JWT_REQUIRED_CLAIMS},
        )
    except jwt.PyJWTError as exc:
        raise DomainError(
            ErrorCode.INVALID_TOKEN,
            "Invalid or expired access token.",
            status_code=401,
        ) from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise DomainError(
            ErrorCode.INVALID_TOKEN,
            "Invalid token type.",
            status_code=401,
        )

    subject = payload.get("sub")
    try:
        return UUID(str(subject))
    except (TypeError, ValueError) as exc:
        raise DomainError(
            ErrorCode.INVALID_TOKEN,
            "Invalid token subject.",
            status_code=401,
        ) from exc


def generate_refresh_token() -> str:
    return token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(refresh_token: str) -> str:
    return sha256(refresh_token.encode("utf-8")).hexdigest()
