"""Per-customer sales-trend features.

Everything here answers "how does this customer's spending behave over
time?" — as opposed to `customer_features.py`, which answers "who is this
customer and how much have they spent in total?". Kept separate so each
module stays a single, readable responsibility.

All functions take a `reference_date` explicitly rather than defaulting to
`today()` internally, because the same code is used to build the
purchase-prediction dataset as of a past cutoff (to avoid label leakage) and
the health-score dataset as of "now" — the caller decides which.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from utils.logging_utils import get_logger

logger = get_logger(__name__)

GROWTH_WINDOW_DAYS = 90


def _seasonal_purchase_pattern(group: pd.DataFrame) -> str:
    revenue_by_quarter = group.groupby("order_quarter")["total_amount"].sum()
    return f"Q{int(revenue_by_quarter.idxmax())}"


def _order_consistency(days_between: pd.Series) -> float:
    """Higher = more predictable order cadence, lower = bursty/erratic.

    Defined as 1 / (1 + coefficient of variation) of the gaps between
    consecutive orders, so it's bounded in (0, 1] and doesn't blow up when
    the mean gap is small. A customer with a single order has no gap to
    measure consistency from, so we return NaN (filled with the population
    median downstream, same convention as any other engineered feature that
    only makes sense with >= 2 observations).
    """
    days_between = days_between.dropna()
    if len(days_between) < 2 or days_between.mean() == 0:
        return np.nan
    cv = days_between.std() / days_between.mean()
    return float(1 / (1 + cv))


def _revenue_growth(orders: pd.DataFrame, reference_date: pd.Timestamp) -> float:
    recent_start = reference_date - pd.Timedelta(days=GROWTH_WINDOW_DAYS)
    prior_start = reference_date - pd.Timedelta(days=2 * GROWTH_WINDOW_DAYS)

    recent = orders.loc[orders["order_date"] > recent_start, "total_amount"].sum()
    prior = orders.loc[
        (orders["order_date"] > prior_start) & (orders["order_date"] <= recent_start), "total_amount"
    ].sum()

    if prior == 0:
        return 0.0
    return float((recent - prior) / prior * 100)


def build_sales_features(orders_time: pd.DataFrame, reference_date: pd.Timestamp) -> pd.DataFrame:
    """Builds one row per `college_id` with monthly/quarterly revenue,
    seasonal pattern, revenue growth, and order consistency.

    `orders_time` must already have the columns `time_features.add_time_features`
    adds (`order_quarter`, `days_since_prev_order`, ...) and must be filtered
    to `order_date <= reference_date` by the caller (feature computation must
    never see data past its own reference point).
    """
    rows = []
    for college_id, group in orders_time.groupby("college_id"):
        months_active = group["order_date"].dt.to_period("M").nunique()
        quarters_active = group["order_date"].dt.to_period("Q").nunique()
        total_revenue = group["total_amount"].sum()

        rows.append(
            {
                "college_id": college_id,
                "monthly_revenue": total_revenue / months_active if months_active else 0.0,
                "quarterly_revenue": total_revenue / quarters_active if quarters_active else 0.0,
                "seasonal_purchase_pattern": _seasonal_purchase_pattern(group),
                "revenue_growth": _revenue_growth(group, reference_date),
                "order_consistency": _order_consistency(group["days_since_prev_order"]),
            }
        )

    features = pd.DataFrame(rows)
    median_consistency = features["order_consistency"].median()
    n_missing = features["order_consistency"].isna().sum()
    if n_missing:
        logger.info(
            "order_consistency undefined for %d single-order customer(s) — filled with population median %.3f",
            n_missing,
            median_consistency,
        )
    features["order_consistency"] = features["order_consistency"].fillna(median_consistency)

    logger.info("Built sales-trend features for %d customers", len(features))
    return features
