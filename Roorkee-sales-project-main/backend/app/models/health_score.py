from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CustomerHealthScore(Base):
    """One row per scoring run per college (append-only time series).

    Kept as a time series — rather than one row updated in place — so
    "health trend" (is this customer improving or declining?) can be read
    directly from history instead of needing a separate change-log, and so a
    change in scoring weights/model_version never destroys the prior record
    of what the score used to be. See PROJECT_SPEC.md section 4.2.
    """

    __tablename__ = "customer_health_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    score_date: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    health_score: Mapped[float] = mapped_column(Float, nullable=False)
    health_status: Mapped[str] = mapped_column(
        Enum("healthy", "at_risk", "critical", name="health_status_enum"), nullable=False, index=True
    )

    # RFM sub-scores (0-100 each), kept alongside the composite for the
    # explainability work planned for a later milestone.
    rfm_recency: Mapped[float] = mapped_column(Float, nullable=False)
    rfm_frequency: Mapped[float] = mapped_column(Float, nullable=False)
    rfm_monetary: Mapped[float] = mapped_column(Float, nullable=False)

    # Full per-factor breakdown (raw value, normalized score, weight,
    # contribution) for every factor in the weighted model — the audit trail
    # behind "explain how every score was calculated".
    component_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)

    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    college: Mapped["College"] = relationship(back_populates="health_scores")
