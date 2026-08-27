import datetime as dt

from pydantic import BaseModel, ConfigDict


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class UserOut(BaseModel):
    # `from_attributes` lets this be built directly from the SQLAlchemy
    # `User` ORM object (`GET /auth/me` returns it as-is) rather than
    # requiring the router to hand-build a dict first.
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: dt.datetime
