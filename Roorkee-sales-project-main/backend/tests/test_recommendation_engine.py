"""Pure-logic tests for the Recommendation Engine (Milestone 9) — no DB
needed since `rules.py` and `priority_engine.py` are plain-value transforms,
same testing approach as `ml/tests/test_explainability_utils.py`.
"""

from app.recommendation_engine import priority_engine, rules
from app.recommendation_engine.config import CONTACT, REGIONAL, RISK, SALES_TREND


def _customer_signals(**overrides) -> rules.CustomerSignals:
    defaults = dict(
        college_id=1,
        name="ABC College",
        institution_type="government",
        region="South",
        state="Tamil Nadu",
        health_score=82.0,
        health_status="healthy",
        purchase_probability=94.0,
        expected_order_value=200_000.0,
        expected_revenue=120_000.0,
        customer_lifetime_value=500_000.0,
        purchase_frequency=1.5,
        seasonal_purchasing_consistency=0.8,
        revenue_growth_pct=10.0,
        days_since_last_purchase=10.0,
        average_payment_delay=0.0,
        max_expected_revenue=120_000.0,
    )
    defaults.update(overrides)
    return rules.CustomerSignals(**defaults)


def test_priority_band_for_contact_matches_milestone_9_literal_example():
    # IF Purchase Probability > 85% AND Health Score > 70 THEN Priority = High
    assert priority_engine.band_for_contact(purchase_probability=94, health_score=82) == "high"
    assert priority_engine.band_for_contact(purchase_probability=90, health_score=60) == "medium"
    assert priority_engine.band_for_contact(purchase_probability=70, health_score=90) == "medium"


def test_contact_rule_fires_above_probability_floor_and_carries_expected_reason():
    signals = _customer_signals()
    rec = rules._rule_contact_high_probability(signals)
    assert rec is not None
    assert rec.recommendation_type == "customer"
    assert rec.priority == "high"
    assert "Contact ABC College this week." == rec.title
    assert "Purchase Probability = 94%" in rec.reason
    assert "Health Score = 82" in rec.reason


def test_contact_rule_does_not_fire_below_probability_floor():
    signals = _customer_signals(purchase_probability=CONTACT.min_purchase_probability - 1)
    assert rules._rule_contact_high_probability(signals) is None


def test_low_health_followup_rule_fires_below_threshold():
    signals = _customer_signals(health_score=RISK.low_health_score - 1, purchase_probability=20)
    rec = rules._rule_low_health_followup(signals)
    assert rec is not None
    assert rec.recommendation_type == "risk"
    assert "follow-up" in rec.title.lower()


def test_low_health_followup_rule_does_not_fire_at_or_above_threshold():
    signals = _customer_signals(health_score=RISK.low_health_score)
    assert rules._rule_low_health_followup(signals) is None


def test_dormant_customer_rule_fires_past_threshold_and_names_the_gap():
    signals = _customer_signals(days_since_last_purchase=200)
    rec = rules._rule_dormant_customer(signals)
    assert rec is not None
    assert "200 days" in rec.title
    assert "Schedule a follow-up meeting" in rec.title


def test_dormant_customer_rule_does_not_fire_below_threshold():
    signals = _customer_signals(days_since_last_purchase=RISK.dormant_days - 1)
    assert rules._rule_dormant_customer(signals) is None


def test_regional_decline_rule_fires_past_threshold():
    signals = rules.RegionSignals(
        region="Delhi", revenue=84_000, previous_revenue=100_000, growth_pct=-16.0, orders=10, max_revenue=200_000
    )
    rec = rules._rule_regional_decline(signals)
    assert rec is not None
    assert "Delhi" in rec.title
    assert "declined by 16%" in rec.title
    assert "admission season" in rec.title


def test_regional_decline_rule_ignores_thin_samples():
    signals = rules.RegionSignals(
        region="Delhi", revenue=1_000, previous_revenue=2_000, growth_pct=-50.0,
        orders=REGIONAL.min_orders_sample - 1, max_revenue=200_000,
    )
    assert rules._rule_regional_decline(signals) is None


def test_regional_growth_rule_fires_past_threshold():
    signals = rules.RegionSignals(
        region="Karnataka", revenue=130_000, previous_revenue=100_000, growth_pct=30.0, orders=10, max_revenue=200_000
    )
    rec = rules._rule_regional_growth(signals)
    assert rec is not None
    assert "growing strongly" in rec.title


def test_rising_demand_rule_fires_and_falling_demand_rule_does_not():
    signals = rules.SalesTrendSignals(
        current_month_revenue=50_000,
        previous_month_revenue=1_000_000,
        actual_growth_pct=-95.0,
        expected_next_period_revenue=1_200_000,
        forecast_change_pct=20.0,
    )
    rising = rules._rule_rising_demand(signals)
    falling = rules._rule_falling_demand(signals)
    assert rising is not None
    assert "increasing" in rising.title
    assert "Prepare additional inventory" in rising.title
    assert falling is None


def test_falling_demand_rule_fires_below_threshold():
    signals = rules.SalesTrendSignals(
        current_month_revenue=50_000,
        previous_month_revenue=1_000_000,
        actual_growth_pct=-95.0,
        expected_next_period_revenue=850_000,
        forecast_change_pct=-15.0,
    )
    rec = rules._rule_falling_demand(signals)
    assert rec is not None
    assert "declining" in rec.title


def test_evaluate_customer_rules_and_risk_rules_can_both_fire_for_the_same_customer():
    # A customer can simultaneously be a contact opportunity by probability
    # and, if the other signals qualify, a risk case — the two rule families
    # are independent and don't suppress each other.
    signals = _customer_signals(purchase_probability=90, health_score=30, days_since_last_purchase=200)
    customer_recs = rules.evaluate_customer_rules([signals])
    risk_recs = rules.evaluate_risk_rules([signals])
    assert len(customer_recs) == 1
    assert len(risk_recs) == 2  # both low-health and dormant fire


def test_recommendation_to_dict_rounds_priority_score():
    rec = rules.Recommendation(
        rule_id="x", recommendation_type="customer", priority="high", priority_score=71.23456,
        title="t", reason="r",
    )
    assert rec.to_dict()["priority_score"] == 71.23
