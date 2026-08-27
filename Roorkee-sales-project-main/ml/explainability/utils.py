"""Shared utilities: SHAP aggregation (dummy columns -> original features)
and turning that into plain-English sentences a sales manager can act on
without knowing what SHAP is.
"""

from __future__ import annotations

import numpy as np


def _origin_of(encoded_column: str, categorical_cols: list[str], numeric_cols: list[str]) -> str:
    for col in numeric_cols:
        if encoded_column == f"{col}_scaled":
            return col
    for col in categorical_cols:
        if encoded_column.startswith(f"{col}_"):
            return col
    return encoded_column  # shouldn't happen for a well-formed model input frame


def aggregate_row(
    shap_row: np.ndarray, encoded_columns: list[str], categorical_cols: list[str], numeric_cols: list[str]
) -> dict[str, float]:
    """Sums one-hot dummy-column SHAP values back to their original feature.

    Exact, not approximate: SHAP values are additive by construction, so a
    categorical feature's total contribution is just the sum of its dummy
    columns' contributions.
    """
    aggregated: dict[str, float] = {}
    for value, col in zip(shap_row, encoded_columns):
        origin = _origin_of(col, categorical_cols, numeric_cols)
        aggregated[origin] = aggregated.get(origin, 0.0) + float(value)
    return aggregated


def aggregate_matrix(
    matrix: np.ndarray, encoded_columns: list[str], categorical_cols: list[str], numeric_cols: list[str]
) -> tuple[np.ndarray, list[str]]:
    """Aggregates a full (n_samples, n_encoded_features) SHAP matrix down to
    (n_samples, n_original_features), with a stable feature order — used by
    the plotting functions, which need every row aggregated the same way
    (unlike `aggregate_row`, which is fine to call independently per row for
    per-customer explanations where order doesn't matter).
    """
    feature_names = numeric_cols + categorical_cols
    aggregated = np.zeros((matrix.shape[0], len(feature_names)))
    for row_idx in range(matrix.shape[0]):
        row_totals = aggregate_row(matrix[row_idx], encoded_columns, categorical_cols, numeric_cols)
        for col_idx, name in enumerate(feature_names):
            aggregated[row_idx, col_idx] = row_totals.get(name, 0.0)
    return aggregated, feature_names


def top_contributors(aggregated: dict[str, float], top_n: int = 5) -> list[dict]:
    ranked = sorted(aggregated.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_n]
    return [
        {"feature": feature, "value": round(value, 4), "direction": "increases" if value > 0 else "decreases"}
        for feature, value in ranked
    ]


# --------------------------------------------------------------------------
# Business-friendly sentences
# --------------------------------------------------------------------------
# Each template takes (direction, raw_value) and returns one short sentence.
# `raw_value` is the customer's actual value for that feature (not the SHAP
# number) — that's what makes "Payment delayed by 18 days" possible instead
# of a generic "payment delay contributed -0.11".

PHRASE_TEMPLATES = {
    "days_since_last_purchase": lambda d, v: (
        f"Recently active, last order {v:.0f} days ago" if d == "increases" else f"No purchases in the last {v:.0f} days"
    ),
    "purchase_frequency": lambda d, v: (
        "Orders regularly and frequently" if d == "increases" else "Orders infrequently compared to peers"
    ),
    "customer_lifetime_value": lambda d, v: (
        "High customer lifetime value" if d == "increases" else "Lower lifetime value than peers"
    ),
    "average_order_value": lambda d, v: (
        "Places large orders on average" if d == "increases" else "Places smaller orders on average"
    ),
    "monthly_revenue": lambda d, v: (
        "Strong recent revenue contribution" if d == "increases" else "Lower recent revenue contribution"
    ),
    "active_months": lambda d, v: (
        f"Long-tenured, active for {v:.0f} months" if d == "increases" else "Shorter engagement history"
    ),
    "average_payment_delay": lambda d, v: (
        f"Payment delayed by {v:.0f} days" if d == "decreases" and v > 0 else "Pays on time or early"
    ),
    "health_score": lambda d, v: (
        "Strong overall customer health score" if d == "increases" else "Below-average customer health score"
    ),
    "revenue_growth": lambda d, v: (
        "Revenue trending upward recently" if d == "increases" else "Revenue trending downward recently"
    ),
    "order_count_growth": lambda d, v: (
        "Ordering more often than before" if d == "increases" else "Ordering less often than before"
    ),
    "preferred_product_category": lambda d, v: (
        f"Frequently purchases {v} equipment" if d == "increases" else f"Limited engagement with {v} category"
    ),
    "seasonal_purchase_pattern": lambda d, v: (
        f"Strong seasonal buyer ({v})" if d == "increases" else "No strong seasonal buying pattern"
    ),
    "institution_type": lambda d, v: (
        f"{str(v).replace('_', ' ').title()} institutions like this one order reliably"
        if d == "increases"
        else f"{str(v).replace('_', ' ').title()} institutions order less predictably"
    ),
    "state": lambda d, v: (
        f"Based in {v}, a strong-performing region" if d == "increases" else f"Based in {v}, a slower-performing region"
    ),
}


def build_reason_sentences(contributors: list[dict], raw_values: dict) -> list[str]:
    """One "+ ..." / "- ..." sentence per contributor, business-manager
    readable — no feature names, no numbers unless they're immediately
    meaningful (days, counts).
    """
    sentences = []
    for c in contributors:
        feature, direction = c["feature"], c["direction"]
        template = PHRASE_TEMPLATES.get(feature)
        raw = raw_values.get(feature)
        if template is None or raw is None:
            sentence = f"{feature.replace('_', ' ').capitalize()} ({direction} likelihood)"
        else:
            sentence = template(direction, raw)
        prefix = "+" if direction == "increases" else "-"
        sentences.append(f"{prefix} {sentence}")
    return sentences
