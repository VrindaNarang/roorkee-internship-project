from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import InvalidTokenError, decode_access_token
from app.core.config import get_settings
from app.db.session import get_db
from app.models import User

settings = get_settings()
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: str = Depends(_oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Decodes the bearer token and loads the corresponding active user.

    Registered as a dependency on every protected router (see `api.py`) —
    individual route functions don't each need `Depends(get_current_user)`
    sprinkled through them.
    """
    try:
        payload = decode_access_token(token)
    except InvalidTokenError as exc:
        raise _CREDENTIALS_ERROR from exc

    email = payload.get("sub")
    if not email:
        raise _CREDENTIALS_ERROR

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """Dependency factory for the handful of endpoints that need more than
    "any logged-in user" — e.g. `Depends(require_role("admin", "sales_manager"))`.

    A factory (not a single function) so each call site can name exactly the
    roles it allows, without a combinatorial explosion of dependency
    functions — one new restricted endpoint is one `require_role(...)` call,
    not a new function in this module.
    """

    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of these roles: {', '.join(allowed_roles)}.",
            )
        return user

    return _check
