from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Five customer segments (Milestone 12: expanded from government/private only —
# see alembic revision b3f7a1d9c264). Order matches the enum's on-disk label
# order (new values are always appended, never inserted/reordered by Postgres).
INSTITUTION_TYPES = ("government", "private", "university", "research_lab", "industry")


class College(Base):
    """A customer institution (the entity that places orders)."""

    __tablename__ = "colleges"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    institution_type: Mapped[str] = mapped_column(
        Enum(*INSTITUTION_TYPES, name="institution_type_enum"), nullable=False
    )
    region: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(150), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(150), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    onboarded_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "dormant", name="college_status_enum"), nullable=False, default="active"
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="college")
    health_scores: Mapped[list["CustomerHealthScore"]] = relationship(back_populates="college")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="college")
