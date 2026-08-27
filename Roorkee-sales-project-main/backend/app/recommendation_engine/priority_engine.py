"""Pure priority-scoring math for the Recommendation Engine (Milestone 9).

Kept separate from `rules.py` (which decides *whether* a recommendation
fires and *what it says*) so "how urgent is this" can be tuned independently
of rule conditions — the same separation `health_score/scoring.py` keeps
from `health_score/config.py`. No database access here.

Two things live here, and they answer different questions:

- `band_for_*` functions decide the High/Medium/Low label. For the one rule
  PROJECT_SPEC gives a literal threshold for (customer contact: probability
  > 85% AND health score > 70 -> High), the band follows that rule exactly
  (`band_for_contact`). Every other recommendation type has no such literal
  spec, so its band comes from a continuous 0-100 urgency score crossing
  `PRIORITY_BANDS` cutoffs (`band_for_score`).
- `score_*` functions produce that continuous 0-100 score, always used for
  *ranking* (so recommendations within — and across — types can be sorted
  consistently), even for customer-contact recommendations where the band
  itself is decided by the literal rule instead of the score.
"""

from __future__ import annotations

from app.recommendation_engine.config import CONTACT, PRIORITY_BANDS


def _clip(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def band_for_score(score: float) -> str:
    """Generic score -> band mapping, used by every rule type except the
    literal customer-contact rule (see `band_for_contact`)."""
    if score >= PRIORITY_BANDS.high_min:
        return "high"
    if score >= PRIORITY_BANDS.medium_min:
        return "medium"
    return "low"


def band_for_contact(*, purchase_probability: float, health_score: float) -> str:
    """Milestone 9's literal rule: `IF Purchase Probability > 85% AND Health
    Score > 70 THEN Priority = High`, applied exactly as specified. Below
    that combination, priority degrades to "medium" rather than being
    all-or-nothing — a 90%-probability account with a mediocre health score
    still deserves proactive outreach, just not top-of-list urgency.
    """
    if purchase_probability > CONTACT.high_priority_probability and health_score > CONTACT.high_priority_health_score:
        return "high"
    return "medium"


def _revenue_component(expected_revenue: float, max_expected_revenue: float) -> float:
    """Scales revenue-at-stake against the current batch's maximum so a
    ₹12L opportunity always outranks a ₹50k one regardless of the dataset's
    absolute revenue scale — the same percentile-style rationale
    `health_score/scoring.py` uses for open-ended monetary factors, without
    needing a full `PercentileRanker` for a single comparison.
    """
    if max_expected_revenue <= 0:
        return 0.0
    return _clip(expected_revenue / max_expected_revenue * 100)


def score_customer_contact(
    *, purchase_probability: float, health_score: float, expected_revenue: float, max_expected_revenue: float
) -> float:
    """0-100 urgency score for "contact this customer" recommendations —
    used only for ranking; the High/Medium band itself comes from
    `band_for_contact`.
    """
    revenue_component = _revenue_component(expected_revenue, max_expected_revenue)
    return _clip(purchase_probability * 0.45 + health_score * 0.35 + revenue_component * 0.20)


def score_risk(
    *,
    days_since_last_purchase: float,
    health_score: float,
    expected_revenue: float,
    max_expected_revenue: float,
    dormant_saturation_days: float = 365.0,
) -> float:
    """Higher urgency = more overdue, lower health, more revenue at risk of
    being lost. Health score carries the most weight (not recency): a
    customer can have a deeply critical health score (e.g. 25/100 — already
    "critical" by `health_score/config.py`'s own bands) while still being
    only moderately overdue, and that should still surface as at least
    medium priority rather than being diluted by a merely-average recency
    figure.
    """
    recency_component = _clip(days_since_last_purchase / dormant_saturation_days * 100)
    poor_health_component = _clip(100 - health_score)
    revenue_component = _revenue_component(expected_revenue, max_expected_revenue)
    return _clip(recency_component * 0.35 + poor_health_component * 0.50 + revenue_component * 0.15)


def score_regional(*, growth_pct: float, revenue: float, max_revenue: float, saturation_pct: float = 40.0) -> float:
    """Severity of the swing (decline OR growth) plus how much revenue rides
    on that region — a sharp decline in a high-revenue region should rank
    above a similar swing somewhere marginal.
    """
    magnitude_component = _clip(abs(growth_pct) / saturation_pct * 100)
    revenue_component = _revenue_component(revenue, max_revenue)
    return _clip(magnitude_component * 0.65 + revenue_component * 0.35)


def score_sales_trend(*, change_pct: float, saturation_pct: float = 30.0) -> float:
    """Company-wide forecast swings have no per-row revenue to weigh against
    (a single aggregate signal, not one row per entity), so magnitude alone
    drives urgency.
    """
    return _clip(abs(change_pct) / saturation_pct * 100)
