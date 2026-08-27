"""Pure scoring math: turn one customer's raw factor values into a weighted,
explainable 0-100 health score.

No database access and no I/O here on purpose — everything in this module is
a plain-value transform, which is what makes it trivially unit-testable and
reusable from both the live service (`health_service.py`) and, later, batch
scoring jobs.

Two normalization strategies are used, matched to what makes sense per
factor (see `config.py` for the rationale):

- **Threshold-based** (`_normalize_threshold`): clipped-linear against an
  explicit "excellent"/"poor" cutoff. Used for recency, payment delay, and
  growth — factors with a business-meaningful absolute definition of good/bad.
- **Percentile rank** (`percentile_rank`): a factor's standing relative to
  the *current* customer population. Used for the open-ended monetary/volume
  factors (CLV, AOV, order count, revenue, frequency, tenure) instead of
  hardcoded dollar/count thresholds that would need constant manual
  retuning as the business grows — this is what "do not hardcode arbitrary
  scores" rules out.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from app.health_score.config import SCORE_BANDS, THRESHOLDS
from app.health_score.weights import LOWER_IS_BETTER, WEIGHTS

_WEIGHT_SUM = sum(WEIGHTS.values())
if abs(_WEIGHT_SUM - 1.0) > 1e-6:
    raise ValueError(f"health_score WEIGHTS must sum to 1.0, got {_WEIGHT_SUM}")


@dataclass
class CustomerFactors:
    """Raw, un-normalized inputs for one customer — exactly the ten factors
    Milestone 6 asks for, computed by `health_service.py` from Postgres.
    """

    college_id: int
    days_since_last_purchase: float
    purchase_frequency: float
    customer_lifetime_value: float
    average_order_value: float
    average_payment_delay: float
    number_of_orders: float
    revenue_generated: float
    seasonal_purchasing_consistency: float  # already 0-1 (see ml pipeline's order_consistency)
    months_active: float
    order_growth_trend: float  # percent


@dataclass
class ComponentScore:
    raw_value: float
    normalized_score: float  # 0-100
    weight: float
    contribution: float  # normalized_score * weight

    def to_dict(self) -> dict:
        return {
            "raw_value": round(self.raw_value, 4),
            "normalized_score": round(self.normalized_score, 2),
            "weight": self.weight,
            "contribution": round(self.contribution, 2),
        }


@dataclass
class HealthScoreResult:
    college_id: int
    health_score: float
    health_status: str
    rfm_recency: float
    rfm_frequency: float
    rfm_monetary: float
    breakdown: dict[str, ComponentScore] = field(default_factory=dict)

    def breakdown_as_dict(self) -> dict:
        return {name: comp.to_dict() for name, comp in self.breakdown.items()}


def _clip(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _normalize_threshold(value: float, excellent: float, poor: float) -> float:
    """Clipped-linear scale between two business-defined cutoffs.

    Handles both directions transparently: if `excellent < poor` a lower raw
    value is better (e.g. recency, payment delay); if `excellent > poor` a
    higher raw value is better (e.g. growth).
    """
    if excellent == poor:
        return 100.0
    fraction = (value - poor) / (excellent - poor)
    return _clip(fraction * 100.0)


class PercentileRanker:
    """Fits once on a population of values, then ranks any value against it.

    Rank = fraction of the population <= value, expressed 0-100. Built with
    `bisect` (stdlib) rather than a full stats dependency since this only
    ever runs over the customer base (tens to low thousands of rows).
    """

    def __init__(self, population: list[float]) -> None:
        self._sorted = sorted(population)
        self._n = len(self._sorted)

    def rank(self, value: float) -> float:
        if self._n == 0:
            return 50.0  # no population to compare against — neutral score
        if self._n == 1:
            return 100.0
        position = bisect.bisect_right(self._sorted, value)
        return _clip(position / self._n * 100.0)


def _normalize_factor(
    factor_name: str, value: float, rankers: dict[str, PercentileRanker]
) -> float:
    if factor_name == "days_since_last_purchase":
        return _normalize_threshold(value, THRESHOLDS.recency_excellent_days, THRESHOLDS.recency_poor_days)
    if factor_name == "average_payment_delay":
        return _normalize_threshold(
            value, THRESHOLDS.payment_delay_excellent_days, THRESHOLDS.payment_delay_poor_days
        )
    if factor_name == "order_growth_trend":
        return _normalize_threshold(value, THRESHOLDS.growth_excellent_pct, THRESHOLDS.growth_poor_pct)
    if factor_name == "seasonal_purchasing_consistency":
        # Already a bounded 0-1 metric (see ml/feature_engineering's
        # order_consistency) — a direct rescale, no peer comparison needed.
        return _clip(value * 100.0)
    # Everything else (frequency, CLV, AOV, order count, revenue, tenure) is
    # open-ended, so it's scored relative to the current customer population.
    return rankers[factor_name].rank(value)


def build_rankers(all_factors: list[CustomerFactors]) -> dict[str, PercentileRanker]:
    """Fits one PercentileRanker per percentile-scored factor, over the
    whole batch. Must be built once from the full customer population and
    reused for every customer in that same scoring run, otherwise "percentile"
    is meaningless.
    """
    percentile_fields = [name for name in WEIGHTS if name not in LOWER_IS_BETTER | {
        "order_growth_trend", "seasonal_purchasing_consistency"
    }]
    return {
        field_name: PercentileRanker([getattr(f, field_name) for f in all_factors])
        for field_name in percentile_fields
    }


def score_customer(factors: CustomerFactors, rankers: dict[str, PercentileRanker]) -> HealthScoreResult:
    breakdown: dict[str, ComponentScore] = {}
    total = 0.0

    for factor_name, weight in WEIGHTS.items():
        raw_value = getattr(factors, factor_name)
        normalized = _normalize_factor(factor_name, raw_value, rankers)
        contribution = normalized * weight
        breakdown[factor_name] = ComponentScore(
            raw_value=raw_value, normalized_score=normalized, weight=weight, contribution=contribution
        )
        total += contribution

    health_score = round(_clip(total), 2)
    status = SCORE_BANDS.status_for(health_score)

    # RFM sub-scores, stored alongside the composite for later explainability
    # work: Recency = the recency component alone; Frequency = the average of
    # the frequency-shaped factors; Monetary = the average of the value-shaped
    # factors.
    rfm_recency = breakdown["days_since_last_purchase"].normalized_score
    rfm_frequency = round(
        (
            breakdown["purchase_frequency"].normalized_score
            + breakdown["number_of_orders"].normalized_score
            + breakdown["months_active"].normalized_score
        )
        / 3,
        2,
    )
    rfm_monetary = round(
        (
            breakdown["customer_lifetime_value"].normalized_score
            + breakdown["average_order_value"].normalized_score
            + breakdown["revenue_generated"].normalized_score
        )
        / 3,
        2,
    )

    return HealthScoreResult(
        college_id=factors.college_id,
        health_score=health_score,
        health_status=status,
        rfm_recency=rfm_recency,
        rfm_frequency=rfm_frequency,
        rfm_monetary=rfm_monetary,
        breakdown=breakdown,
    )


def score_all(all_factors: list[CustomerFactors]) -> list[HealthScoreResult]:
    """Scores an entire batch of customers, sharing one set of percentile
    rankers fitted on the batch — the entrypoint `health_service.py` calls.
    """
    rankers = build_rankers(all_factors)
    return [score_customer(f, rankers) for f in all_factors]
