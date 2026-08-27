"""CLI entrypoint for the feature-engineering pipeline.

Usage:
    cd ml
    .venv/Scripts/python.exe run_pipeline.py
"""

from __future__ import annotations

import pandas as pd

from pipeline import MLPipeline
from utils.logging_utils import get_logger

logger = get_logger(__name__)

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)


def main() -> None:
    logger.info("Starting SalesPilot AI feature-engineering pipeline")
    pipeline = MLPipeline()
    result = pipeline.run()

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"Customer Health Score dataset:      {result.customer_health_dataset.shape}")
    print(f"Purchase Prediction dataset:        {result.purchase_prediction_dataset.shape}")
    print(f"Product Features dataset:           {result.product_features_dataset.shape}")

    print("\n--- Sample: Customer Health Score dataset (5 rows) ---")
    print(
        result.customer_health_dataset[
            [
                "college_id",
                "name",
                "institution_type",
                "total_orders",
                "customer_lifetime_value",
                "average_order_value",
                "days_since_last_purchase",
                "average_payment_delay",
                "preferred_product_category",
                "risk_category",
            ]
        ].head(5)
    )

    print("\n--- Sample: Purchase Prediction dataset (5 rows) ---")
    print(
        result.purchase_prediction_dataset[
            [
                "college_id",
                "name",
                "days_since_last_purchase",
                "purchase_frequency",
                "revenue_growth",
                "order_consistency",
                "purchased_in_next_30_days",
            ]
        ].head(5)
    )

    print("\n--- Sample: Product Features dataset (5 rows) ---")
    print(
        result.product_features_dataset[
            ["product_id", "sku", "name", "category", "units_sold", "revenue_contribution_pct", "product_popularity_score"]
        ].head(5)
    )
    print()


if __name__ == "__main__":
    main()
