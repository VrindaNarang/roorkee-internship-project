from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Prediction(Base):
    """One row per (college, prediction_type) per scoring run — see
    PROJECT_SPEC.md section 4.2. `shap_explanation` is reserved for a later
    milestone and stays null until then.
    """

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_type: Mapped[str] = mapped_column(
        Enum("purchase_probability", "expected_order_value", name="prediction_type_enum"),
        nullable=False,
        index=True,
    )
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_date: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    shap_explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    college: Mapped["College"] = relationship(back_populates="predictions")
