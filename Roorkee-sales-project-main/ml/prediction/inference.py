"""Pure inference: feature rows + loaded models -> predictions.

No I/O here — `predict.py` is responsible for building the feature
DataFrame (from Postgres) and for writing results back out. Keeping this
module I/O-free is what makes it trivially unit-testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from prediction.config import ALL_FEATURES
from prediction.model_loader import LoadedModels


def _confidence_from_probability(probability: np.ndarray) -> np.ndarray:
    """0 = coin-flip uncertain, 1 = fully confident either way.

    Deliberately derived from the classifier's own probability output rather
    than a second model — a probability of 0.5 carries no information, while
    0.05 or 0.95 both represent the model being equally sure of its answer.
    """
    return np.abs(probability - 0.5) * 2


def build_model_input(models: LoadedModels, feature_df: pd.DataFrame) -> pd.DataFrame:
    """Encodes `feature_df` into the exact column set/order both models were
    trained on. Shared by `predict_batch` and the SHAP explanation step in
    `predict.py` so both always score the same encoded representation.
    """
    missing = [c for c in ALL_FEATURES if c not in feature_df.columns]
    if missing:
        raise ValueError(f"feature_df is missing required columns: {missing}")

    encoded = models.encoder.transform(feature_df[["college_id", *ALL_FEATURES]])
    return encoded[
        models.encoder.one_hot.get_feature_names_out(models.encoder.categorical_cols).tolist()
        + [f"{c}_scaled" for c in models.encoder.numeric_cols]
    ]


def predict_batch(models: LoadedModels, feature_df: pd.DataFrame) -> pd.DataFrame:
    """Scores every row in `feature_df` (one row per college).

    `feature_df` must contain `college_id` plus every column in
    `prediction.config.ALL_FEATURES` — see `train.py`'s `build_feature_frame`
    for how that frame is assembled.
    """
    model_input = build_model_input(models, feature_df)

    probability = models.classifier.predict_proba(model_input)[:, 1]
    expected_value_given_purchase = models.regressor.predict(model_input)
    # Expected revenue = P(purchase) * E[order value | purchase] — the single
    # number a sales manager can rank "who's worth calling" by, combining
    # both models rather than picking one in isolation.
    expected_revenue = probability * np.clip(expected_value_given_purchase, a_min=0, a_max=None)

    return pd.DataFrame(
        {
            "college_id": feature_df["college_id"].values,
            "purchase_probability": probability,
            "expected_order_value": np.clip(expected_value_given_purchase, a_min=0, a_max=None),
            "expected_revenue": expected_revenue,
            "confidence_score": _confidence_from_probability(probability),
        }
    )
