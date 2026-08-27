"""Orchestrates the full feature-engineering pipeline:

    Load Data -> Preprocess -> Engineer Features -> Generate ML Dataset -> Save

Exposed as a `MLPipeline` class (for programmatic/test use) and driven by
`run_pipeline.py` for the `python run_pipeline.py` CLI entrypoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from config.settings import Settings, get_settings
from feature_engineering.customer_features import build_customer_features
from feature_engineering.product_features import build_product_features
from feature_engineering.sales_features import build_sales_features
from feature_engineering.time_features import add_time_features
from preprocessing.cleaning import clean_all
from preprocessing.encoding import FeatureEncoder
from preprocessing.loaders import get_engine, load_raw_tables
from preprocessing.outliers import OutlierCapper
from utils.logging_utils import get_logger

logger = get_logger(__name__)

AT_RISK_DAYS = 120  # same recency-based business rule used by the dashboard's analytics service
GROWTH_WINDOW_DAYS = 90


def _order_count_growth(in_scope: pd.DataFrame, reference_date: pd.Timestamp) -> pd.Series:
    """Percent change in order *count* between the 90 days before
    `reference_date` and the 90 days before that. Mirrors
    `sales_features._revenue_growth`'s windowing but counts orders instead of
    summing revenue.
    """
    recent_start = reference_date - pd.Timedelta(days=GROWTH_WINDOW_DAYS)
    prior_start = reference_date - pd.Timedelta(days=2 * GROWTH_WINDOW_DAYS)

    recent = in_scope[in_scope["order_date"] > recent_start].groupby("college_id").size()
    prior = in_scope[
        (in_scope["order_date"] > prior_start) & (in_scope["order_date"] <= recent_start)
    ].groupby("college_id").size()

    growth = ((recent - prior) / prior.replace(0, pd.NA) * 100).fillna(0.0)
    return growth


# Columns encoded/scaled for the model-ready variant of each dataset. Kept
# explicit (rather than "encode every categorical/numeric column") so the
# human-readable id/name/label columns survive untouched into the model-ready
# file too, for traceability between the two.
CUSTOMER_CATEGORICAL_COLS = [
    "institution_type",
    "region",
    "state",
    "preferred_product_category",
    "seasonal_purchase_pattern",
]
CUSTOMER_NUMERIC_COLS = [
    "tenure_days",
    "total_orders",
    "customer_lifetime_value",
    "average_order_value",
    "average_payment_delay",
    "active_months",
    "purchase_frequency",
    "days_since_last_purchase",
    "monthly_revenue",
    "quarterly_revenue",
    "revenue_growth",
    "order_consistency",
    "order_count_growth",
]


@dataclass
class PipelineResult:
    customer_health_dataset: pd.DataFrame
    purchase_prediction_dataset: pd.DataFrame
    product_features_dataset: pd.DataFrame
    customer_health_dataset_encoded: pd.DataFrame = field(repr=False)
    purchase_prediction_dataset_encoded: pd.DataFrame = field(repr=False)


class MLPipeline:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Stage 1: Load
    # ------------------------------------------------------------------
    def load(self) -> dict[str, pd.DataFrame]:
        logger.info("=== Stage 1/5: Load ===")
        engine = get_engine(self.settings)
        return load_raw_tables(engine)

    # ------------------------------------------------------------------
    # Stage 2: Preprocess
    # ------------------------------------------------------------------
    def preprocess(self, raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        logger.info("=== Stage 2/5: Preprocess ===")
        cleaned = clean_all(raw)

        order_capper = OutlierCapper(columns=["total_amount", "subtotal", "tax_amount"]).fit(
            cleaned["orders"]
        )
        cleaned["orders"] = order_capper.transform(cleaned["orders"], table_name="orders")
        order_capper.save(self.settings.artifacts_dir / "orders_outlier_bounds.json")

        item_capper = OutlierCapper(columns=["quantity", "line_total"]).fit(cleaned["order_items"])
        cleaned["order_items"] = item_capper.transform(cleaned["order_items"], table_name="order_items")
        item_capper.save(self.settings.artifacts_dir / "order_items_outlier_bounds.json")

        product_capper = OutlierCapper(columns=["unit_price"]).fit(cleaned["products"])
        cleaned["products"] = product_capper.transform(cleaned["products"], table_name="products")
        product_capper.save(self.settings.artifacts_dir / "products_outlier_bounds.json")

        return cleaned

    # ------------------------------------------------------------------
    # Stage 3: Engineer features
    # ------------------------------------------------------------------
    def engineer_features(self, cleaned: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        logger.info("=== Stage 3/5: Engineer Features ===")
        orders_time = add_time_features(cleaned["orders"], self.settings)

        product_features = build_product_features(
            cleaned["order_items"], cleaned["products"], cleaned["product_categories"]
        )

        return {"orders_time": orders_time, "product_features": product_features}

    def _build_dataset(
        self,
        colleges: pd.DataFrame,
        orders_time: pd.DataFrame,
        order_items: pd.DataFrame,
        products: pd.DataFrame,
        categories: pd.DataFrame,
        reference_date: pd.Timestamp,
    ) -> pd.DataFrame:
        in_scope = orders_time[orders_time["order_date"] <= reference_date]
        customer_feats = build_customer_features(
            colleges, in_scope, order_items, products, categories, reference_date
        )
        sales_feats = build_sales_features(in_scope, reference_date)
        return customer_feats.merge(sales_feats, on="college_id", how="left")

    # ------------------------------------------------------------------
    # Stage 4: Generate ML datasets
    # ------------------------------------------------------------------
    def generate_datasets(
        self, cleaned: dict[str, pd.DataFrame], engineered: dict[str, pd.DataFrame]
    ) -> PipelineResult:
        logger.info("=== Stage 4/5: Generate ML Datasets ===")
        orders_time = engineered["orders_time"]
        full_reference_date = orders_time["order_date"].max()
        cutoff_date = full_reference_date - pd.Timedelta(days=self.settings.prediction_horizon_days)
        logger.info(
            "Reference date (health dataset) = %s | cutoff date (purchase-prediction dataset) = %s",
            full_reference_date.date(),
            cutoff_date.date(),
        )

        # --- Customer Health Score dataset: full history, "as of now" ---
        health_dataset = self._build_dataset(
            cleaned["colleges"],
            orders_time,
            cleaned["order_items"],
            cleaned["products"],
            cleaned["product_categories"],
            full_reference_date,
        )
        health_dataset["risk_category"] = health_dataset.apply(
            lambda row: "dormant"
            if row["status"] == "dormant"
            else ("at_risk" if row["days_since_last_purchase"] > AT_RISK_DAYS else "healthy"),
            axis=1,
        )
        health_dataset["order_count_growth"] = health_dataset["college_id"].map(
            _order_count_growth(in_scope=orders_time, reference_date=full_reference_date)
        ).fillna(0.0)

        # --- Purchase Prediction dataset: features as of `cutoff_date`, label
        #     observed in the (cutoff_date, full_reference_date] window that
        #     follows it. Computing features and label from disjoint time
        #     windows is what keeps this a valid supervised-learning dataset
        #     instead of a leaky one. ---
        purchase_dataset = self._build_dataset(
            cleaned["colleges"],
            orders_time,
            cleaned["order_items"],
            cleaned["products"],
            cleaned["product_categories"],
            cutoff_date,
        )
        future_window = orders_time[
            (orders_time["order_date"] > cutoff_date) & (orders_time["order_date"] <= full_reference_date)
        ]
        future_buyers = set(future_window["college_id"])
        purchase_dataset["purchased_in_next_30_days"] = (
            purchase_dataset["college_id"].isin(future_buyers).astype(int)
        )
        # Regression target for Milestone 7: total revenue each college actually
        # generated in the label window. 0 for colleges that didn't buy — this
        # is deliberately the same disjoint window as the classification label
        # so both targets are computed from data the "as of cutoff" features
        # couldn't have seen.
        next_order_value = future_window.groupby("college_id")["total_amount"].sum()
        purchase_dataset["next_order_value"] = (
            purchase_dataset["college_id"].map(next_order_value).fillna(0.0)
        )
        logger.info(
            "Purchase-prediction label balance: %d positive / %d total (%.1f%%)",
            purchase_dataset["purchased_in_next_30_days"].sum(),
            len(purchase_dataset),
            purchase_dataset["purchased_in_next_30_days"].mean() * 100,
        )

        # "Order growth" feature: change in order *count* (not revenue) between
        # the 90 days immediately before cutoff and the 90 days before that —
        # complements `revenue_growth` (which tracks value) with a pure
        # cadence/volume trend signal, computed only from data <= cutoff_date
        # so it's leakage-free like every other purchase-prediction feature.
        purchase_dataset["order_count_growth"] = purchase_dataset["college_id"].map(
            _order_count_growth(in_scope=orders_time[orders_time["order_date"] <= cutoff_date], reference_date=cutoff_date)
        ).fillna(0.0)

        health_encoded = FeatureEncoder(CUSTOMER_CATEGORICAL_COLS, CUSTOMER_NUMERIC_COLS).fit_transform(
            health_dataset
        )
        purchase_encoded = FeatureEncoder(CUSTOMER_CATEGORICAL_COLS, CUSTOMER_NUMERIC_COLS).fit_transform(
            purchase_dataset
        )

        return PipelineResult(
            customer_health_dataset=health_dataset,
            purchase_prediction_dataset=purchase_dataset,
            product_features_dataset=engineered["product_features"],
            customer_health_dataset_encoded=health_encoded,
            purchase_prediction_dataset_encoded=purchase_encoded,
        )

    # ------------------------------------------------------------------
    # Stage 5: Save
    # ------------------------------------------------------------------
    def save(self, result: PipelineResult) -> dict[str, str]:
        logger.info("=== Stage 5/5: Save Processed Datasets ===")
        paths = {
            "customer_health_dataset": self.settings.datasets_dir / "customer_health_score_dataset.csv",
            "customer_health_dataset_encoded": self.settings.datasets_dir
            / "customer_health_score_dataset_encoded.csv",
            "purchase_prediction_dataset": self.settings.datasets_dir / "purchase_prediction_dataset.csv",
            "purchase_prediction_dataset_encoded": self.settings.datasets_dir
            / "purchase_prediction_dataset_encoded.csv",
            "product_features_dataset": self.settings.datasets_dir / "product_features_dataset.csv",
        }
        for attr, path in paths.items():
            df = getattr(result, attr)
            df.to_csv(path, index=False)
            logger.info("Saved %s (%d rows, %d columns) -> %s", attr, len(df), df.shape[1], path)
        return {k: str(v) for k, v in paths.items()}

    def run(self) -> PipelineResult:
        raw = self.load()
        cleaned = self.preprocess(raw)
        engineered = self.engineer_features(cleaned)
        result = self.generate_datasets(cleaned, engineered)
        self.save(result)
        return result
