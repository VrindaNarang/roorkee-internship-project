"""Pure security primitives: password hashing and JWT encode/decode.

No database access here on purpose (mirrors `health_score/scoring.py`'s
"pure math, no I/O" convention) — this module is trivially unit-testable and
reusable from both the login flow and any future service that needs a token.
"""

from __future__ import annotations

import datetime as dt

import bcrypt
import jwt

from app.core.config import get_settings


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(*, subject: str, role: str, expires_minutes: int | None = None) -> str:
    """`subject` is the user's email (unique, human-readable — no separate
    username field exists). `role` is embedded in the token so
    `require_role()` can check it without a DB round trip per request.
    """
    settings = get_settings()
    expires_delta = dt.timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


class InvalidTokenError(Exception):
    """Raised for any decode failure (expired, malformed, bad signature) —
    callers don't need to distinguish which; it's always an unauthenticated
    request either way."""


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
