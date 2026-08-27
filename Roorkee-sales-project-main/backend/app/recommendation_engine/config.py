"""Tunable thresholds for the Business Recommendation Engine (Milestone 9).

Kept separate from `rules.py`/`priority_engine.py` so a manager can retune
"what counts as urgent enough to act on" without touching rule conditions or
scoring math — same separation `app/health_score/config.py` keeps from
`scoring.py`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContactThresholds:
    """'Contact this customer' rule. Milestone 9's literal example:
    IF Purchase Probability > 85% AND Health Score > 70 THEN Priority = High.
    """

    min_purchase_probability: float = 60.0  # floor to generate a contact recommendation at all
    high_priority_probability: float = 85.0
    high_priority_health_score: float = 70.0


@dataclass(frozen=True)
class RiskThresholds:
    """Risk / follow-up rules."""

    low_health_score: float = 40.0  # IF Health Score < 40 THEN Recommend Follow-up
    dormant_days: float = 180.0  # "has not purchased in 180 days" -> schedule a follow-up meeting
    dormant_saturation_days: float = 365.0  # urgency maxes out at a year of inactivity


@dataclass(frozen=True)
class RegionalThresholds:
    """Regional revenue-trend rules — 90-day recent vs. prior window, same
    definition as `health_score.health_service._revenue_growth`."""

    decline_pct: float = 15.0  # IF Revenue Down > 15% THEN Recommend Regional Campaign
    growth_pct: float = 20.0  # symmetric "opportunity" side — strong growth worth reinforcing
    min_orders_sample: int = 3  # ignore regions with too few orders to trust a growth % on
    swing_saturation_pct: float = 40.0  # |growth %| beyond this is treated as maximally urgent


@dataclass(frozen=True)
class SalesTrendThresholds:
    """Company-wide next-30-days demand-forecast rules (predicted vs. last
    completed month's actual revenue)."""

    increase_pct: float = 10.0
    decrease_pct: float = 10.0
    swing_saturation_pct: float = 30.0


@dataclass(frozen=True)
class PriorityBands:
    """0-100 priority score -> High/Medium/Low band. Shared by every
    recommendation type that doesn't have its own literal band rule (see
    `priority_engine.band_for_contact` for the one that does), so urgency is
    comparable across customer, risk, regional, and sales recommendations.
    """

    high_min: float = 70.0
    medium_min: float = 40.0
    # anything below medium_min is "low"


CONTACT = ContactThresholds()
RISK = RiskThresholds()
REGIONAL = RegionalThresholds()
SALES_TREND = SalesTrendThresholds()
PRIORITY_BANDS = PriorityBands()
