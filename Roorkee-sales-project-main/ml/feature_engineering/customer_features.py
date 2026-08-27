"""Per-customer RFM / engagement / payment-behavior features.

These are the classic "who is this customer" features that both downstream
datasets (purchase prediction, customer health) are built on:
recency/frequency/monetary, tenure, payment reliability, and category
preference. See `sales_features.py` for the complementary revenue-trend
features.
"""

from __future__ import annotations

import pandas as pd

from utils.logging_utils import get_logger

logger = get_logger(__name__)


def _payment_delay_days(orders: pd.DataFrame, reference_date: pd.Timestamp) -> pd.Series:
    """Days late per order.

    - Paid orders: `payment_received_date - payment_due_date` (negative means
      paid early).
    - Unpaid orders past their due date: `reference_date - payment_due_date`,
      i.e. the delay accrued *so far* — the order is still a live risk signal
      even though it hasn't been paid yet.
    - Unpaid orders not yet due: excluded (no delay to measure).
    """
    paid = orders["payment_received_date"].notna()
    overdue_unpaid = ~paid & (reference_date > orders["payment_due_date"])

    delay = pd.Series(float("nan"), index=orders.index, dtype="float64")
    delay.loc[paid] = (
        orders.loc[paid, "payment_received_date"] - orders.loc[paid, "payment_due_date"]
    ).dt.days
    delay.loc[overdue_unpaid] = (reference_date - orders.loc[overdue_unpaid, "payment_due_date"]).dt.days
    return delay


def _preferred_category(order_items_enriched: pd.DataFrame) -> pd.DataFrame:
    revenue_by_college_category = (
        order_items_enriched.groupby(["college_id", "category_name"])["line_total"].sum().reset_index()
    )
    idx = revenue_by_college_category.groupby("college_id")["line_total"].idxmax()
    preferred = revenue_by_college_category.loc[idx, ["college_id", "category_name"]]
    return preferred.rename(columns={"category_name": "preferred_product_category"})


def build_customer_features(
    colleges: pd.DataFrame,
    orders_time: pd.DataFrame,
    order_items: pd.DataFrame,
    products: pd.DataFrame,
    categories: pd.DataFrame,
    reference_date: pd.Timestamp,
) -> pd.DataFrame:
    """Builds one row per college with RFM/CLV/payment/category features.

    `orders_time` must already be filtered to `order_date <= reference_date`.
    Colleges with no qualifying orders still get a row (zero-filled) so the
    dataset represents the full customer base, not just active buyers.
    """
    orders_time = orders_time.copy()
    orders_time["payment_delay_days"] = _payment_delay_days(orders_time, reference_date)

    agg = orders_time.groupby("college_id").agg(
        total_orders=("id", "count"),
        customer_lifetime_value=("total_amount", "sum"),
        average_order_value=("total_amount", "mean"),
        last_order_date=("order_date", "max"),
        average_payment_delay=("payment_delay_days", "mean"),
    )
    agg["active_months"] = orders_time.groupby("college_id")["order_date"].apply(
        lambda s: s.dt.to_period("M").nunique()
    )
    agg["days_since_last_purchase"] = (reference_date - agg["last_order_date"]).dt.days
    agg["purchase_frequency"] = agg["total_orders"] / agg["active_months"].replace(0, pd.NA)
    agg["average_payment_delay"] = agg["average_payment_delay"].fillna(0.0)
    agg = agg.reset_index()

    # Preferred category needs order_items joined to products/categories,
    # then restricted to the orders in scope (<= reference_date).
    items_enriched = (
        order_items.merge(products[["id", "category_id"]], left_on="product_id", right_on="id", suffixes=("", "_product"))
        .merge(categories[["id", "name"]].rename(columns={"name": "category_name"}), left_on="category_id", right_on="id", suffixes=("", "_category"))
        .merge(orders_time[["id", "college_id"]], left_on="order_id", right_on="id", suffixes=("", "_order"))
    )
    preferred = _preferred_category(items_enriched)

    features = colleges[
        ["id", "name", "institution_type", "region", "state", "status", "onboarded_date"]
    ].rename(columns={"id": "college_id"})
    features["tenure_days"] = (reference_date - features["onboarded_date"]).dt.days

    features = features.merge(agg, on="college_id", how="left").merge(preferred, on="college_id", how="left")

    zero_fill_cols = [
        "total_orders",
        "customer_lifetime_value",
        "average_order_value",
        "average_payment_delay",
        "active_months",
        "purchase_frequency",
    ]
    features[zero_fill_cols] = features[zero_fill_cols].fillna(0)
    # A customer who has never ordered has been "waiting" for their entire
    # tenure — a meaningful recency value, not a missing one.
    features["days_since_last_purchase"] = features["days_since_last_purchase"].fillna(features["tenure_days"])
    features["preferred_product_category"] = features["preferred_product_category"].fillna("None")

    logger.info(
        "Built customer features for %d colleges (%d with >=1 order in scope)",
        len(features),
        int((features["total_orders"] > 0).sum()),
    )
    return features.drop(columns=["last_order_date"], errors="ignore")
