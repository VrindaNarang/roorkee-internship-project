from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Three roles only, per Milestone 11's brief — no open-ended role system.
# Ordered here from most to least privileged for readability; the actual
# hierarchy (which role can do what) lives in `app/auth/dependencies.py`.
USER_ROLES = ("admin", "sales_manager", "sales_executive")


class User(Base):
    """An authenticated application user (see PROJECT_SPEC.md Milestone 11).

    Deliberately minimal — no password reset flow, no email verification, no
    org/tenant model — this is single-tenant internal software, not a
    multi-tenant SaaS product.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(Enum(*USER_ROLES, name="user_role_enum"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
