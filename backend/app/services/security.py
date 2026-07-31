from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings


settings = get_settings()
password_hasher = PasswordHasher()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(account_id: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes,
    )
    payload = {
        "sub": str(account_id),
        "type": "access",
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except InvalidTokenError:
        return None

    if payload.get("type") != "access":
        return None

    subject = payload.get("sub")
    try:
        return int(subject)
    except (TypeError, ValueError):
        return None


def create_delete_confirmation_token(*, account_id: int, email: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.delete_token_expire_minutes,
    )
    payload: dict[str, Any] = {
        "sub": str(account_id),
        "type": "delete_confirmation",
        "email": email.lower(),
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_delete_confirmation_token(token: str) -> tuple[int, str] | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except InvalidTokenError:
        return None

    if payload.get("type") != "delete_confirmation":
        return None

    try:
        account_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None

    email = payload.get("email")
    if not isinstance(email, str) or not email:
        return None

    return account_id, email
