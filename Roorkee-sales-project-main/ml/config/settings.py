"""Central configuration for the ML feature-engineering pipeline.

Reads the same root `.env` the backend uses (single source of truth for
`DATABASE_URL`) so the pipeline always reads from the same Postgres instance
the dashboard is backed by.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ML_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ML_ROOT.parent

load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://salespilot:salespilot_dev_password@127.0.0.1:5433/salespilot",
        )
    )

    datasets_dir: Path = ML_ROOT / "datasets"
    artifacts_dir: Path = ML_ROOT / "artifacts" / "preprocessing"

    # India-specific business calendar constants used by time feature engineering.
    financial_year_start_month: int = 4  # FY runs Apr -> Mar
    # Academic admission cycle for a lab-equipment-to-colleges business:
    # new academic year intake + related bulk equipment purchases.
    admission_season_months: tuple[int, ...] = (6, 7, 8)
    # Odd semester (Jul-Dec) vs even semester (Jan-Jun) is the standard Indian
    # academic-calendar split used to explain seasonal ordering patterns.
    odd_semester_months: tuple[int, ...] = (7, 8, 9, 10, 11, 12)

    # Outlier detection: IQR multiplier for Tukey's fences.
    outlier_iqr_multiplier: float = 1.5

    # Reference window (days) used to build the purchase-prediction label
    # without leaking future data into the feature computation.
    prediction_horizon_days: int = 30

    def __post_init__(self) -> None:
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()
