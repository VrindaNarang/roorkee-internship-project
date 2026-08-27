"""Tunable thresholds and score bands for the Customer Health Scoring engine.

Kept separate from `weights.py` on purpose: this file answers "what counts
as excellent/poor for a given factor" (business-interpretable cutoffs),
`weights.py` answers "how much does each factor matter" (relative
importance). Changing either never requires touching `scoring.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

MODEL_VERSION = "health_score_v1"


@dataclass(frozen=True)
class ScoreBands:
    """0-100 health score -> status label. Matches Milestone 6's spec exactly."""

    healthy_min: float = 80.0
    at_risk_min: float = 50.0
    # anything below at_risk_min is "critical"

    def status_for(self, score: float) -> str:
        if score >= self.healthy_min:
            return "healthy"
        if score >= self.at_risk_min:
            return "at_risk"
        return "critical"


@dataclass(frozen=True)
class ThresholdConfig:
    """Absolute, business-interpretable cutoffs for the factors that aren't
    scored relative to the peer population (recency, payment delay, growth).

    These are recency/rate metrics where an absolute definition of "good"
    makes business sense on its own (e.g. "no order in 6 months is bad"
    doesn't need to be relative to other customers) — as opposed to monetary
    factors like CLV, which are scored by percentile rank against the
    current customer base instead (see `scoring.percentile_rank`).
    """

    # Days since last purchase: <= excellent -> full recency score; >= poor -> zero.
    recency_excellent_days: float = 30.0
    recency_poor_days: float = 180.0

    # Average payment delay in days (0 = on time, negative = early). Poor is
    # set to 90 (not 30/60) because government-institution customers in this
    # business commonly run NET-60/NET-90 payment cycles by design — see the
    # mock data generator's government-vs-private payment skew — so a slower
    # but bounded cycle shouldn't be indistinguishable from a genuinely
    # delinquent account.
    payment_delay_excellent_days: float = 0.0
    payment_delay_poor_days: float = 90.0

    # Revenue growth %, comparing recent vs prior period (see ml pipeline's
    # `revenue_growth` feature for the same definition).
    growth_excellent_pct: float = 20.0
    growth_poor_pct: float = -50.0


SCORE_BANDS = ScoreBands()
THRESHOLDS = ThresholdConfig()
