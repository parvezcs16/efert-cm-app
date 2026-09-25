import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

settings = get_settings()

_password_hasher = PasswordHasher()

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)

JWT_ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(
    *, employee_id: uuid.UUID, role: str, password_state: str
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + ACCESS_TOKEN_TTL
    payload: dict[str, Any] = {
        "sub": str(employee_id),
        "role": role,
        "pw": password_state,
        "iat": now,
        "exp": expires_at,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])


PURPOSE_TOKEN_TTL = timedelta(minutes=5)


def create_purpose_token(*, subject: str, purpose: str) -> str:
    """Short-lived token proving an OTP for `purpose` was just verified for
    `subject` (a p_no). Used to gate the follow-up step (e.g. set-password)
    without re-sending the OTP, while still expiring quickly."""
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "typ": f"purpose:{purpose}",
        "iat": now,
        "exp": now + PURPOSE_TOKEN_TTL,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_purpose_token(token: str, *, purpose: str, subject: str) -> None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    if payload.get("typ") != f"purpose:{purpose}" or payload.get("sub") != subject:
        raise ValueError("Token does not match this request")


GUEST_ACCESS_TOKEN_TTL = timedelta(hours=2)
GUEST_SESSION_TOKEN_VALIDITY = timedelta(hours=24)


def create_guest_access_token(*, guest_session_id: uuid.UUID) -> tuple[str, datetime]:
    """A short-lived bearer token identifying a guest_session for ordering
    endpoints, exchanged for the long-lived QR token via /guest/auth. Kept
    separate from the employee access token (different "typ", no role/
    password_state claims) so the two can never be confused."""
    now = datetime.now(UTC)
    expires_at = now + GUEST_ACCESS_TOKEN_TTL
    payload: dict[str, Any] = {
        "sub": str(guest_session_id),
        "typ": "guest_session",
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)
    return token, expires_at


def decode_guest_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid or expired guest token") from exc

    if payload.get("typ") != "guest_session":
        raise ValueError("Not a guest session token")

    return uuid.UUID(payload["sub"])
