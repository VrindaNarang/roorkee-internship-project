import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.auth_service import authenticate_user, issue_token_for
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.auth import TokenResponse, UserOut

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    """OAuth2 password grant (standard form fields `username`/`password` —
    `username` holds the user's email). This exact shape is what makes the
    FastAPI/Swagger "Authorize" button work out of the box for `/docs`.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        logger.warning("Failed login attempt for %s", form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = issue_token_for(user)
    logger.info("User %s (%s) logged in", user.email, user.role)
    return TokenResponse(access_token=token, role=user.role, full_name=user.full_name)


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user
