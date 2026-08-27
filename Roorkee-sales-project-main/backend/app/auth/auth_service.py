from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, verify_password
from app.models import User


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Returns the user if the email/password combination is valid and the
    account is active, else None — deliberately not distinguishing "no such
    user" from "wrong password" in the return value (the router turns both
    into the same generic 401, so a caller can't enumerate valid emails).
    """
    user = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def issue_token_for(user: User) -> str:
    return create_access_token(subject=user.email, role=user.role)
