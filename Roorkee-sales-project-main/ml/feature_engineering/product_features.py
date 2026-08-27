"""Per-product features: popularity, category revenue, revenue contribution.

Product-level (rather than customer-level) — a separate table today, but the
natural join key for a future cross-sell/recommendation feature set built on
top of this milestone's output.
"""

from __future__ import annotations

import pandas as pd

from utils.logging_utils import get_logger

logger = get_logger(__name__)


def build_product_features(
    order_items: pd.DataFrame, products: pd.DataFrame, categories: pd.DataFrame
) -> pd.DataFrame:
    sales = order_items.groupby("product_id").agg(
        units_sold=("quantity", "sum"),
        product_revenue=("line_total", "sum"),
    )

    features = products[["id", "sku", "name", "category_id", "unit_price", "is_active"]].rename(
        columns={"id": "product_id"}
    )
    features = features.merge(
        categories[["id", "name"]].rename(columns={"id": "category_id", "name": "category"}),
        on="category_id",
        how="left",
    )
    features = features.merge(sales, on="product_id", how="left")
    features[["units_sold", "product_revenue"]] = features[["units_sold", "product_revenue"]].fillna(0)

    total_revenue = features["product_revenue"].sum()
    features["revenue_contribution_pct"] = (
        features["product_revenue"] / total_revenue * 100 if total_revenue else 0.0
    )

    category_revenue = features.groupby("category")["product_revenue"].transform("sum")
    features["category_revenue"] = category_revenue

    max_units = features["units_sold"].max()
    features["product_popularity_score"] = (
        features["units_sold"] / max_units if max_units else 0.0
    )

    logger.info("Built product features for %d products across %d categories", len(features), features["category"].nunique())
    return features.drop(columns=["category_id"])
