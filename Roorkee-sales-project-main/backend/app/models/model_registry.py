from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelRegistry(Base):
    """Tracks every trained model version (see PROJECT_SPEC.md section 4.2).

    `ml/prediction/train.py` writes rows here directly (via raw SQL — the ml/
    project has its own Python environment and doesn't import the backend's
    ORM). The backend only ever reads this table to find the currently
    active artifact path for each model.
    """

    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    trained_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
