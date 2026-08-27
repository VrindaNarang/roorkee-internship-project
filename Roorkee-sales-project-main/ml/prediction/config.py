"""Configuration for the Purchase Propensity Prediction engine.

Paths, feature lists, hyperparameter search grids, and split ratios all live
here so `train.py`/`predict.py` never hardcode a tunable value inline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from config.settings import ML_ROOT

ARTIFACTS_DIR = ML_ROOT / "artifacts" / "prediction"
MODEL_NAME_CLASSIFIER = "purchase_propensity_classifier"
MODEL_NAME_REGRESSOR = "expected_order_value_regressor"

# --- Feature lists -----------------------------------------------------
# Maps Milestone 7's requested feature names to the columns already produced
# by the Milestone 5 feature-engineering pipeline (+ this milestone's two
# additions in ml/pipeline.py) and the health score joined in from Postgres.
# "Customer Type" and "College Type" both refer to `institution_type`
# (government/private) in this business domain — the same column is used for
# both rather than duplicating it.
NUMERIC_FEATURES: list[str] = [
    "days_since_last_purchase",
    "purchase_frequency",
    "customer_lifetime_value",
    "average_order_value",
    "monthly_revenue",  # "Revenue Generated"
    "active_months",  # "Months Active"
    "average_payment_delay",
    "health_score",
    "revenue_growth",  # "Revenue Trend"
    "order_count_growth",  # "Order Growth"
]
CATEGORICAL_FEATURES: list[str] = [
    "preferred_product_category",
    "seasonal_purchase_pattern",  # "Seasonality"
    "institution_type",  # "Customer Type" / "College Type"
    "state",
]
ALL_FEATURES: list[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

CLASSIFICATION_TARGET = "purchased_in_next_30_days"
REGRESSION_TARGET = "next_order_value"

DEFAULT_HEALTH_SCORE = 50.0  # neutral fallback if a college has no health score row yet


@dataclass(frozen=True)
class SplitConfig:
    test_size: float = 0.2
    val_size: float = 0.2  # fraction of the remaining train+val pool
    random_state: int = 42
    cv_folds_classifier: int = 5
    cv_folds_regressor: int = 3  # regressor trains on a much smaller (purchasers-only) subset


@dataclass(frozen=True)
class SearchSpace:
    """Small, deliberately conservative hyperparameter grids.

    Kept small on purpose: this dataset has ~60 customers (36 positive for
    the regressor), so an exhaustive/aggressive search would overfit the
    validation folds before it ever helps the model generalize.
    """

    classifier_grid: dict = field(
        default_factory=lambda: {
            "n_estimators": [100, 200],
            "max_depth": [2, 3, 4],
            "learning_rate": [0.05, 0.1],
            "min_child_weight": [1, 3],
            "subsample": [0.8, 1.0],
        }
    )
    regressor_grid: dict = field(
        default_factory=lambda: {
            "n_estimators": [100, 200],
            "max_depth": [2, 3],
            "learning_rate": [0.05, 0.1],
            "min_child_weight": [1, 3],
            "subsample": [0.8, 1.0],
        }
    )


SPLIT = SplitConfig()
SEARCH = SearchSpace()


def new_version_dir() -> tuple[str, Path]:
    """Timestamp-based version id + its artifact directory (not yet created)."""
    import datetime as dt

    version = "v" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    return version, ARTIFACTS_DIR / version
