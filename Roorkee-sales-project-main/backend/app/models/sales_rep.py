from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SalesRep(Base):
    __tablename__ = "sales_reps"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    hire_date: Mapped[dt.date] = mapped_column(Date, nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="sales_rep")
