"""High-level SHAP explanation service: model + encoded features in,
business-ready explanations out. This is what `prediction/predict.py` calls
— it never touches `shap` or the raw column-aggregation logic directly.
"""

from __future__ import annotations

import pandas as pd

from explainability.config import TOP_N_GLOBAL, TOP_N_LOCAL
from explainability.explainer import raw_shap_matrix
from explainability.utils import aggregate_row, build_reason_sentences, top_contributors
from utils.logging_utils import get_logger

logger = get_logger(__name__)


def explain_rows(
    model,
    X_encoded: pd.DataFrame,
    raw_feature_rows: list[dict],
    *,
    categorical_cols: list[str],
    numeric_cols: list[str],
    top_n: int = TOP_N_LOCAL,
) -> list[dict]:
    """One explanation per row: top contributors + plain-English reasons.

    `raw_feature_rows[i]` must be the customer's actual (un-encoded) feature
    values for row `i` — needed to phrase reasons like "delayed by 18 days"
    instead of a bare SHAP number.
    """
    matrix = raw_shap_matrix(model, X_encoded)
    encoded_columns = list(X_encoded.columns)

    explanations = []
    for row, raw_values in zip(matrix, raw_feature_rows):
        aggregated = aggregate_row(row, encoded_columns, categorical_cols, numeric_cols)
        contributors = top_contributors(aggregated, top_n)
        positive = [c for c in contributors if c["direction"] == "increases"]
        negative = [c for c in contributors if c["direction"] == "decreases"]
        explanations.append(
            {
                "contributors": contributors,
                "positive_contributors": positive,
                "negative_contributors": negative,
                "reasons": build_reason_sentences(contributors, raw_values),
            }
        )
    logger.info("Computed SHAP explanations for %d rows", len(explanations))
    return explanations


def explain_global(
    model,
    X_encoded: pd.DataFrame,
    *,
    categorical_cols: list[str],
    numeric_cols: list[str],
    top_n: int = TOP_N_GLOBAL,
) -> dict:
    """Mean absolute SHAP contribution per feature across every row —
    "what's driving this overall" plus a one-line plain-English summary.
    """
    matrix = raw_shap_matrix(model, X_encoded)
    encoded_columns = list(X_encoded.columns)

    totals: dict[str, list[float]] = {}
    for row in matrix:
        aggregated = aggregate_row(row, encoded_columns, categorical_cols, numeric_cols)
        for feature, value in aggregated.items():
            totals.setdefault(feature, []).append(abs(value))

    mean_importance = {feature: float(sum(values) / len(values)) for feature, values in totals.items()}
    ranked = sorted(mean_importance.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    top_features = [{"feature": feature, "mean_abs_contribution": round(value, 4)} for feature, value in ranked]

    top_names = [_pretty(f["feature"]) for f in top_features[:3]]
    summary_text = (
        f"Across all customers, {', '.join(top_names)} are the strongest drivers of this prediction."
        if top_names
        else "Not enough data yet to summarize what drives this prediction."
    )

    return {"top_features": top_features, "summary_text": summary_text}


def _pretty(feature: str) -> str:
    return feature.replace("_", " ")
