"""Time-based features, computed per order row.

These feed the customer/sales aggregations downstream (e.g. `quarter` is
needed to compute quarterly revenue, `days_since_prev_order` is needed to
compute order-cadence consistency) and are also useful features in their own
right for a model that should learn seasonal buying behavior.
"""

from __future__ import annotations

import pandas as pd

from config.settings import Settings, get_settings
from utils.logging_utils import get_logger

logger = get_logger(__name__)


def _financial_year(dates: pd.Series, fy_start_month: int) -> pd.Series:
    """India-style financial year label, e.g. 2025-07-01 -> 'FY2025-26'."""
    fy_start_year = dates.dt.year.where(dates.dt.month >= fy_start_month, dates.dt.year - 1)
    return "FY" + fy_start_year.astype(str) + "-" + (fy_start_year + 1).astype(str).str[-2:]


def add_time_features(orders: pd.DataFrame, settings: Settings | None = None) -> pd.DataFrame:
    """Adds month/quarter/financial_year/semester/admission-season/days-between-orders.

    Expects a cleaned `orders` DataFrame with a datetime `order_date` column
    and a `college_id` column. Returns a copy — never mutates the input.
    """
    settings = settings or get_settings()
    df = orders.copy()

    df["order_month"] = df["order_date"].dt.month
    df["order_quarter"] = df["order_date"].dt.quarter
    df["financial_year"] = _financial_year(df["order_date"], settings.financial_year_start_month)

    df["semester_season"] = df["order_month"].apply(
        lambda m: "Odd Semester" if m in settings.odd_semester_months else "Even Semester"
    )
    df["admission_season_indicator"] = (
        df["order_month"].isin(settings.admission_season_months).astype(int)
    )

    # Days since this college's previous order — the raw signal behind both
    # "order consistency" (its variance) and per-order recency.
    df = df.sort_values(["college_id", "order_date"])
    df["days_since_prev_order"] = (
        df.groupby("college_id")["order_date"].diff().dt.days
    )

    logger.info(
        "Added time features to %d order rows (%d distinct financial years)",
        len(df),
        df["financial_year"].nunique(),
    )
    return df.reset_index(drop=True)
