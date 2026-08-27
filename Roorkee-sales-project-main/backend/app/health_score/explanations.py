"""Turns a health score's `component_breakdown` into plain-English reasons.

The weighted formula in `scoring.py` already IS its own exact Shapley-style
decomposition (see PROJECT_SPEC.md section 6a): for a linear weighted sum,
each factor's `contribution` is precisely its attribution to the total
score — no approximate explainer needed. This module just phrases that
attribution the same way `ml/explainability/utils.py` phrases SHAP
contributions for the purchase-prediction models, so all three "models"
(health score, purchase probability, expected order value) read consistently
in the Explainability tab.
"""

from __future__ import annotations

PHRASE_TEMPLATES = {
    "days_since_last_purchase": lambda positive, raw: (
        f"Recently active, last order {raw:.0f} days ago" if positive else f"No purchases in the last {raw:.0f} days"
    ),
    "purchase_frequency": lambda positive, raw: (
        "Orders regularly and frequently" if positive else "Orders infrequently compared to peers"
    ),
    "customer_lifetime_value": lambda positive, raw: (
        "High customer lifetime value" if positive else "Lower lifetime value than peers"
    ),
    "average_order_value": lambda positive, raw: (
        "Places large orders on average" if positive else "Places smaller orders on average"
    ),
    "average_payment_delay": lambda positive, raw: (
        "Pays on time or early" if positive else f"Payment delayed by {raw:.0f} days"
    ),
    "number_of_orders": lambda positive, raw: (
        f"Strong order history ({raw:.0f} orders)" if positive else f"Limited order history ({raw:.0f} orders)"
    ),
    "revenue_generated": lambda positive, raw: (
        "Strong recent revenue contribution" if positive else "Lower recent revenue contribution"
    ),
    "order_growth_trend": lambda positive, raw: (
        "Order volume trending upward" if positive else "Order volume trending downward"
    ),
    "seasonal_purchasing_consistency": lambda positive, raw: (
        "Orders every semester, like clockwork" if positive else "Irregular, unpredictable ordering pattern"
    ),
    "months_active": lambda positive, raw: (
        f"Long-tenured, active for {raw:.0f} months" if positive else "Shorter engagement history"
    ),
}


def build_health_score_reasons(component_breakdown: dict, top_n: int = 5) -> list[str]:
    """Ranks factors by `abs(contribution)` (their actual weighted impact on
    the 0-100 score) and phrases the top N as "+ ..." / "- ..." sentences.
    """
    ranked = sorted(component_breakdown.items(), key=lambda kv: abs(kv[1]["contribution"]), reverse=True)[:top_n]

    sentences = []
    for factor, detail in ranked:
        positive = detail["normalized_score"] >= 50  # above/below the midpoint of this factor's own 0-100 scale
        raw = detail["raw_value"]
        template = PHRASE_TEMPLATES.get(factor)
        sentence = template(positive, raw) if template else f"{factor.replace('_', ' ').capitalize()}"
        prefix = "+" if positive else "-"
        sentences.append(f"{prefix} {sentence}")
    return sentences
