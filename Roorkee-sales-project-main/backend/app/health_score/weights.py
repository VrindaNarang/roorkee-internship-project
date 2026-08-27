"""Factor weights for the Customer Health Score.

The single place to retune "what matters most" without touching any scoring
logic. Every factor listed in Milestone 6's spec has an entry here, and the
weights must sum to 1.0 (`scoring.py` validates this at import time so a bad
edit fails loudly rather than silently skewing every score).

Weighting rationale:
- Recency (`days_since_last_purchase`) and payment reliability
  (`average_payment_delay`) get the largest individual weights — they're the
  two classic leading indicators of churn in a B2B/institutional-sales
  context, ahead of pure volume/monetary size.
- Growth trend is weighted on par with frequency/CLV/orders/revenue — a
  customer shrinking fast is a risk signal independent of how big they are.
- Seasonal consistency and tenure (months active) get the smallest weights:
  useful context, but weaker standalone predictors than the others.
"""

from __future__ import annotations

WEIGHTS: dict[str, float] = {
    "days_since_last_purchase": 0.20,
    "average_payment_delay": 0.15,
    "purchase_frequency": 0.10,
    "customer_lifetime_value": 0.10,
    "number_of_orders": 0.10,
    "revenue_generated": 0.10,
    "order_growth_trend": 0.10,
    "average_order_value": 0.05,
    "seasonal_purchasing_consistency": 0.05,
    "months_active": 0.05,
}

# Which direction is "good" for each factor — needed by scoring.py to decide
# whether a higher raw value should normalize to a higher or lower score.
LOWER_IS_BETTER: set[str] = {"days_since_last_purchase", "average_payment_delay"}
