"""Configurable business rules for the Recommendation Engine (Milestone 9).

Each rule is a small `condition(signals) -> bool` + `build(signals) ->
Recommendation` pair, registered in one of the four `*_RULES` lists below.
Adding a new rule means writing one function and appending one `Rule(...)`
entry — nothing else in this module, `recommendation_service.py`, or the API
layer needs to change.

Pure and DB-free by design (matching `health_score/scoring.py`): every rule
takes an already-assembled signals dataclass and returns a plain
`Recommendation` dataclass. `recommendation_service.py` is the only place
that talks to Postgres or other services.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.recommendation_engine import priority_engine
from app.recommendation_engine.config import CONTACT, REGIONAL, RISK, SALES_TREND


def _format_inr(value: float) -> str:
    """Formats a rupee amount in Lakh/Crore units, matching Milestone 9's
    example reason text ("Expected Revenue = ₹1.2 Lakh")."""
    magnitude = abs(value)
    if magnitude >= 1_00_00_000:
        return f"₹{value / 1_00_00_000:.2f} Cr"
    if magnitude >= 1_00_000:
        return f"₹{value / 1_00_000:.1f} Lakh"
    if magnitude >= 1_000:
        return f"₹{value / 1_000:.1f}K"
    return f"₹{value:.0f}"


# --------------------------------------------------------------------------
# Signals — the inputs each rule family reasons over, assembled by
# recommendation_service.py from HealthScoreService / predictions_service /
# Order+College queries.
# --------------------------------------------------------------------------


@dataclass
class CustomerSignals:
    college_id: int
    name: str
    institution_type: str
    region: str
    state: str
    health_score: float
    health_status: str
    purchase_probability: float  # 0-100; 0 if no prediction exists yet
    expected_order_value: float
    expected_revenue: float
    customer_lifetime_value: float
    purchase_frequency: float
    seasonal_purchasing_consistency: float  # 0-1
    revenue_growth_pct: float  # this customer's own order-growth trend, %
    days_since_last_purchase: float
    average_payment_delay: float
    max_expected_revenue: float  # batch context: highest expected_revenue this run, for scaling


@dataclass
class RegionSignals:
    region: str
    revenue: float  # last 90 days
    previous_revenue: float  # the 90 days before that
    growth_pct: float
    orders: int
    max_revenue: float  # batch context: highest region revenue this run, for scaling


@dataclass
class SalesTrendSignals:
    current_month_revenue: float
    previous_month_revenue: float  # last fully-completed month — the forecast baseline
    actual_growth_pct: float
    expected_next_period_revenue: float  # sum of expected_revenue across current predictions
    forecast_change_pct: float  # expected_next_period_revenue vs. previous_month_revenue


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


@dataclass
class Recommendation:
    rule_id: str
    recommendation_type: str  # "customer" | "risk" | "regional" | "sales"
    priority: str  # "high" | "medium" | "low"
    priority_score: float  # 0-100, for ranking within and across types
    title: str
    reason: str
    college_id: int | None = None
    college_name: str | None = None
    region: str | None = None
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "recommendation_type": self.recommendation_type,
            "priority": self.priority,
            "priority_score": round(self.priority_score, 2),
            "title": self.title,
            "reason": self.reason,
            "college_id": self.college_id,
            "college_name": self.college_name,
            "region": self.region,
            "metrics": self.metrics,
        }


@dataclass(frozen=True)
class Rule:
    rule_id: str
    recommendation_type: str
    description: str  # the IF/THEN business rule, for admin visibility
    evaluate: Callable[[Any], Recommendation | None]


# --------------------------------------------------------------------------
# Customer recommendations — "Contact ABC College this week."
# --------------------------------------------------------------------------


def _rule_contact_high_probability(s: CustomerSignals) -> Recommendation | None:
    if s.purchase_probability < CONTACT.min_purchase_probability:
        return None
    priority = priority_engine.band_for_contact(
        purchase_probability=s.purchase_probability, health_score=s.health_score
    )
    score = priority_engine.score_customer_contact(
        purchase_probability=s.purchase_probability,
        health_score=s.health_score,
        expected_revenue=s.expected_revenue,
        max_expected_revenue=s.max_expected_revenue,
    )
    return Recommendation(
        rule_id="contact_high_probability",
        recommendation_type="customer",
        priority=priority,
        priority_score=score,
        title=f"Contact {s.name} this week.",
        reason=(
            f"Purchase Probability = {s.purchase_probability:.0f}% · "
            f"Health Score = {s.health_score:.0f} · "
            f"Expected Revenue = {_format_inr(s.expected_revenue)}"
        ),
        college_id=s.college_id,
        college_name=s.name,
        region=s.region,
        metrics={
            "purchase_probability": s.purchase_probability,
            "health_score": s.health_score,
            "expected_order_value": s.expected_order_value,
            "expected_revenue": s.expected_revenue,
        },
    )


# --------------------------------------------------------------------------
# Risk recommendations — dormant accounts and declining health scores.
# --------------------------------------------------------------------------


def _rule_low_health_followup(s: CustomerSignals) -> Recommendation | None:
    if s.health_score >= RISK.low_health_score:
        return None
    score = priority_engine.score_risk(
        days_since_last_purchase=s.days_since_last_purchase,
        health_score=s.health_score,
        expected_revenue=s.expected_revenue,
        max_expected_revenue=s.max_expected_revenue,
        dormant_saturation_days=RISK.dormant_saturation_days,
    )
    return Recommendation(
        rule_id="low_health_followup",
        recommendation_type="risk",
        priority=priority_engine.band_for_score(score),
        priority_score=score,
        title=f"{s.name}'s health score has dropped to {s.health_score:.0f}. Recommend a follow-up call.",
        reason=(
            f"Health Score = {s.health_score:.0f} (below the {RISK.low_health_score:.0f} threshold) · "
            f"{s.days_since_last_purchase:.0f} days since last purchase"
        ),
        college_id=s.college_id,
        college_name=s.name,
        region=s.region,
        metrics={"health_score": s.health_score, "days_since_last_purchase": s.days_since_last_purchase},
    )


def _rule_dormant_customer(s: CustomerSignals) -> Recommendation | None:
    if s.days_since_last_purchase < RISK.dormant_days:
        return None
    score = priority_engine.score_risk(
        days_since_last_purchase=s.days_since_last_purchase,
        health_score=s.health_score,
        expected_revenue=s.expected_revenue,
        max_expected_revenue=s.max_expected_revenue,
        dormant_saturation_days=RISK.dormant_saturation_days,
    )
    return Recommendation(
        rule_id="dormant_customer",
        recommendation_type="risk",
        priority=priority_engine.band_for_score(score),
        priority_score=score,
        title=f"{s.name} has not purchased in {s.days_since_last_purchase:.0f} days. Schedule a follow-up meeting.",
        reason=(
            f"Last purchase {s.days_since_last_purchase:.0f} days ago "
            f"(dormant threshold: {RISK.dormant_days:.0f} days) · Health Score = {s.health_score:.0f}"
        ),
        college_id=s.college_id,
        college_name=s.name,
        region=s.region,
        metrics={"days_since_last_purchase": s.days_since_last_purchase, "health_score": s.health_score},
    )


# --------------------------------------------------------------------------
# Regional recommendations — revenue swings worth a business response.
# --------------------------------------------------------------------------


def _rule_regional_decline(s: RegionSignals) -> Recommendation | None:
    if s.orders < REGIONAL.min_orders_sample or s.growth_pct > -REGIONAL.decline_pct:
        return None
    score = priority_engine.score_regional(
        growth_pct=s.growth_pct, revenue=s.revenue, max_revenue=s.max_revenue,
        saturation_pct=REGIONAL.swing_saturation_pct,
    )
    return Recommendation(
        rule_id="regional_revenue_decline",
        recommendation_type="regional",
        priority=priority_engine.band_for_score(score),
        priority_score=score,
        title=(
            f"Revenue in {s.region} has declined by {abs(s.growth_pct):.0f}%. "
            "Increase marketing campaigns before the admission season."
        ),
        reason=(
            f"Revenue moved from {_format_inr(s.previous_revenue)} to {_format_inr(s.revenue)} "
            f"({s.growth_pct:+.0f}%) over the last 90 days"
        ),
        region=s.region,
        metrics={"growth_pct": s.growth_pct, "revenue": s.revenue, "previous_revenue": s.previous_revenue},
    )


def _rule_regional_growth(s: RegionSignals) -> Recommendation | None:
    if s.orders < REGIONAL.min_orders_sample or s.growth_pct < REGIONAL.growth_pct:
        return None
    score = priority_engine.score_regional(
        growth_pct=s.growth_pct, revenue=s.revenue, max_revenue=s.max_revenue,
        saturation_pct=REGIONAL.swing_saturation_pct,
    )
    return Recommendation(
        rule_id="regional_growth_opportunity",
        recommendation_type="regional",
        priority=priority_engine.band_for_score(score),
        priority_score=score,
        title=(
            f"Revenue in {s.region} is growing strongly (+{s.growth_pct:.0f}%). "
            "Increase sales coverage and inventory allocation there."
        ),
        reason=(
            f"Revenue moved from {_format_inr(s.previous_revenue)} to {_format_inr(s.revenue)} "
            f"({s.growth_pct:+.0f}%) over the last 90 days"
        ),
        region=s.region,
        metrics={"growth_pct": s.growth_pct, "revenue": s.revenue, "previous_revenue": s.previous_revenue},
    )


# --------------------------------------------------------------------------
# Sales recommendations — company-wide next-period demand forecast.
# --------------------------------------------------------------------------


def _rule_rising_demand(s: SalesTrendSignals) -> Recommendation | None:
    if s.forecast_change_pct < SALES_TREND.increase_pct:
        return None
    score = priority_engine.score_sales_trend(
        change_pct=s.forecast_change_pct, saturation_pct=SALES_TREND.swing_saturation_pct
    )
    return Recommendation(
        rule_id="rising_demand_forecast",
        recommendation_type="sales",
        priority=priority_engine.band_for_score(score),
        priority_score=score,
        title=f"Expected sales next month are increasing (+{s.forecast_change_pct:.0f}%). Prepare additional inventory.",
        reason=(
            f"Expected revenue from current predictions is {_format_inr(s.expected_next_period_revenue)} "
            f"vs {_format_inr(s.previous_month_revenue)} last month"
        ),
        metrics={
            "forecast_change_pct": s.forecast_change_pct,
            "expected_next_period_revenue": s.expected_next_period_revenue,
            "previous_month_revenue": s.previous_month_revenue,
        },
    )


def _rule_falling_demand(s: SalesTrendSignals) -> Recommendation | None:
    if s.forecast_change_pct > -SALES_TREND.decrease_pct:
        return None
    score = priority_engine.score_sales_trend(
        change_pct=s.forecast_change_pct, saturation_pct=SALES_TREND.swing_saturation_pct
    )
    return Recommendation(
        rule_id="falling_demand_forecast",
        recommendation_type="sales",
        priority=priority_engine.band_for_score(score),
        priority_score=score,
        title=(
            f"Expected sales next month are declining ({s.forecast_change_pct:.0f}%). "
            "Review inventory and promotional plans."
        ),
        reason=(
            f"Expected revenue from current predictions is {_format_inr(s.expected_next_period_revenue)} "
            f"vs {_format_inr(s.previous_month_revenue)} last month"
        ),
        metrics={
            "forecast_change_pct": s.forecast_change_pct,
            "expected_next_period_revenue": s.expected_next_period_revenue,
            "previous_month_revenue": s.previous_month_revenue,
        },
    )


# --------------------------------------------------------------------------
# Rule registries — add a new rule by writing one function above and
# appending one entry below. Nothing else needs to change.
# --------------------------------------------------------------------------

CUSTOMER_RULES: list[Rule] = [
    Rule(
        "contact_high_probability",
        "customer",
        "IF Purchase Probability > 85% AND Health Score > 70 THEN Priority = High (contact this week)",
        _rule_contact_high_probability,
    ),
]

RISK_RULES: list[Rule] = [
    Rule("low_health_followup", "risk", "IF Health Score < 40 THEN Recommend Follow-up", _rule_low_health_followup),
    Rule(
        "dormant_customer",
        "risk",
        "IF Days Since Last Purchase >= 180 THEN Recommend a Follow-up Meeting",
        _rule_dormant_customer,
    ),
]

REGIONAL_RULES: list[Rule] = [
    Rule(
        "regional_revenue_decline",
        "regional",
        "IF Revenue Down > 15% THEN Recommend Regional Campaign",
        _rule_regional_decline,
    ),
    Rule(
        "regional_growth_opportunity",
        "regional",
        "IF Revenue Up > 20% THEN Recommend Expanding Regional Investment",
        _rule_regional_growth,
    ),
]

SALES_RULES: list[Rule] = [
    Rule(
        "rising_demand_forecast",
        "sales",
        "IF Expected Next-Month Revenue Up > 10% THEN Recommend Increasing Inventory",
        _rule_rising_demand,
    ),
    Rule(
        "falling_demand_forecast",
        "sales",
        "IF Expected Next-Month Revenue Down > 10% THEN Recommend Reviewing Inventory/Promotions",
        _rule_falling_demand,
    ),
]

ALL_RULES: list[Rule] = CUSTOMER_RULES + RISK_RULES + REGIONAL_RULES + SALES_RULES


def evaluate_customer_rules(signals: list[CustomerSignals]) -> list[Recommendation]:
    return [rec for s in signals for rule in CUSTOMER_RULES if (rec := rule.evaluate(s)) is not None]


def evaluate_risk_rules(signals: list[CustomerSignals]) -> list[Recommendation]:
    return [rec for s in signals for rule in RISK_RULES if (rec := rule.evaluate(s)) is not None]


def evaluate_regional_rules(signals: list[RegionSignals]) -> list[Recommendation]:
    return [rec for s in signals for rule in REGIONAL_RULES if (rec := rule.evaluate(s)) is not None]


def evaluate_sales_rules(signals: SalesTrendSignals) -> list[Recommendation]:
    return [rec for rule in SALES_RULES if (rec := rule.evaluate(signals)) is not None]
