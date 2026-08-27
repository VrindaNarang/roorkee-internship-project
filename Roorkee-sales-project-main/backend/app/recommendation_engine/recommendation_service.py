"""Orchestrates the Business Recommendation Engine (Milestone 9): pulls
already-computed signals from the Health Score and Purchase Prediction
services plus live order/college aggregates, builds per-entity signal
objects, runs them through `rules.py`, and returns ranked, business-ready
recommendations.

Deliberately NOT persisted to a table: a recommendation is a live view over
data that's already persisted elsewhere (health scores, predictions, orders).
Recomputing on every read means it's always in sync with the latest
health-score/prediction run, with none of the staleness a cached snapshot
would introduce — the same reasoning `explainability_service.py` uses to
compose existing services rather than owning its own data. Signal assembly
(below) carries a short TTL cache (Milestone 11) purely to absorb the burst
of near-simultaneous requests the Recommendations page fires (five endpoints
loading at once each independently need the same signals) — 20-30 seconds
of staleness is invisible to a user but avoids redoing the same
order/college scan five times over.

Kept as a service class (matching `HealthScoreService`) so one DB session
covers a whole recommendation run and API routers stay thin.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache import ttl_cache
from app.health_score.health_service import HealthScoreService
from app.models import College, Order
from app.recommendation_engine import rules
from app.services import predictions_service

logger = logging.getLogger(__name__)

REGIONAL_TREND_WINDOW_DAYS = 90  # recent-vs-prior window, matches health_score's RECENT_WINDOW_DAYS
SIGNALS_CACHE_SECONDS = 20


class RecommendationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._health_service = HealthScoreService(db)

    # ------------------------------------------------------------------
    # Signal assembly
    # ------------------------------------------------------------------
    @ttl_cache(SIGNALS_CACHE_SECONDS)
    def _customer_signals(self) -> list[rules.CustomerSignals]:
        """Builds one CustomerSignals per college with a computed health
        score. Purchase-probability/expected-revenue default to 0 when no
        prediction exists yet (e.g. before the first `POST /ml/retrain`) so
        risk rules — which only depend on health score and recency — still
        fire; only the probability-dependent contact rule is gated on a real
        prediction being present.
        """
        health_items = self._health_service.list_latest()
        factors_by_college = {f.college_id: f for f in self._health_service.compute_factors()}
        predictions_by_college = {p.college_id: p for p in predictions_service.list_predictions(self.db)}

        max_expected_revenue = max((p.expected_revenue for p in predictions_by_college.values()), default=0.0)

        signals = []
        for health in health_items:
            college_id = health["college_id"]
            factors = factors_by_college.get(college_id)
            if factors is None:
                continue
            prediction = predictions_by_college.get(college_id)
            signals.append(
                rules.CustomerSignals(
                    college_id=college_id,
                    name=health["name"],
                    institution_type=health["institution_type"],
                    region=health["region"],
                    state=health["state"],
                    health_score=health["health_score"],
                    health_status=health["health_status"],
                    purchase_probability=prediction.purchase_probability if prediction else 0.0,
                    expected_order_value=prediction.expected_order_value if prediction else 0.0,
                    expected_revenue=prediction.expected_revenue if prediction else 0.0,
                    customer_lifetime_value=factors.customer_lifetime_value,
                    purchase_frequency=factors.purchase_frequency,
                    seasonal_purchasing_consistency=factors.seasonal_purchasing_consistency,
                    revenue_growth_pct=factors.order_growth_trend,
                    days_since_last_purchase=factors.days_since_last_purchase,
                    average_payment_delay=factors.average_payment_delay,
                    max_expected_revenue=max_expected_revenue,
                )
            )
        return signals

    @ttl_cache(SIGNALS_CACHE_SECONDS)
    def _region_signals(self) -> list[rules.RegionSignals]:
        """Recent-90-days vs. prior-90-days revenue per region, the same
        rolling-window growth definition `health_service._revenue_growth`
        uses per customer, just grouped by region instead.
        """
        today = date.today()
        recent_start = today - timedelta(days=REGIONAL_TREND_WINDOW_DAYS)
        prior_start = today - timedelta(days=2 * REGIONAL_TREND_WINDOW_DAYS)

        rows = (
            self.db.query(College.region, Order.total_amount, Order.order_date)
            .join(Order, Order.college_id == College.id)
            .filter(Order.order_date > prior_start)
            .all()
        )

        recent_revenue: dict[str, float] = defaultdict(float)
        prior_revenue: dict[str, float] = defaultdict(float)
        orders_count: dict[str, int] = defaultdict(int)
        for region, total_amount, order_date in rows:
            orders_count[region] += 1
            if order_date > recent_start:
                recent_revenue[region] += float(total_amount)
            else:
                prior_revenue[region] += float(total_amount)

        regions = set(recent_revenue) | set(prior_revenue)
        max_revenue = max(recent_revenue.values(), default=0.0)

        signals = []
        for region in regions:
            revenue = recent_revenue.get(region, 0.0)
            previous = prior_revenue.get(region, 0.0)
            growth_pct = (revenue - previous) / previous * 100 if previous else 0.0
            signals.append(
                rules.RegionSignals(
                    region=region,
                    revenue=revenue,
                    previous_revenue=previous,
                    growth_pct=round(growth_pct, 2),
                    orders=orders_count[region],
                    max_revenue=max_revenue,
                )
            )
        return signals

    @ttl_cache(SIGNALS_CACHE_SECONDS)
    def _sales_trend_signals(self) -> rules.SalesTrendSignals:
        """Compares the model's next-30-days expected revenue (sum of every
        current prediction's `expected_revenue`) against last month's
        *actual* revenue — not the current, still-in-progress month, which
        would understate the baseline and make the forecast swing look
        artificially large early in the month.
        """
        today = date.today()
        month_start = today.replace(day=1)
        prev_month_end = month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        current_month_revenue = (
            self.db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(Order.order_date >= month_start, Order.order_date <= today)
            .scalar()
            or 0
        )
        previous_month_revenue = (
            self.db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(Order.order_date >= prev_month_start, Order.order_date <= prev_month_end)
            .scalar()
            or 0
        )
        actual_growth_pct = (
            (float(current_month_revenue) - float(previous_month_revenue)) / float(previous_month_revenue) * 100
            if previous_month_revenue
            else 0.0
        )

        predictions = predictions_service.list_predictions(self.db)
        expected_next_period_revenue = sum(p.expected_revenue for p in predictions)
        baseline = float(previous_month_revenue)
        forecast_change_pct = (
            (expected_next_period_revenue - baseline) / baseline * 100 if baseline else 0.0
        )

        return rules.SalesTrendSignals(
            current_month_revenue=float(current_month_revenue),
            previous_month_revenue=baseline,
            actual_growth_pct=round(actual_growth_pct, 2),
            expected_next_period_revenue=round(expected_next_period_revenue, 2),
            forecast_change_pct=round(forecast_change_pct, 2),
        )

    # ------------------------------------------------------------------
    # Recommendation generation (read path)
    # ------------------------------------------------------------------
    def generate_customer_recommendations(self) -> list[dict]:
        """'Contact this week' recommendations, one per customer worth
        proactive outreach right now."""
        items = [r.to_dict() for r in rules.evaluate_customer_rules(self._customer_signals())]
        items.sort(key=lambda r: r["priority_score"], reverse=True)
        return items

    def generate_risk_recommendations(self) -> list[dict]:
        """Customers who need a proactive follow-up: dormant or low health score."""
        items = [r.to_dict() for r in rules.evaluate_risk_rules(self._customer_signals())]
        items.sort(key=lambda r: r["priority_score"], reverse=True)
        return items

    def generate_regional_recommendations(self) -> list[dict]:
        """Regional revenue swings (decline or growth) worth a business response."""
        items = [r.to_dict() for r in rules.evaluate_regional_rules(self._region_signals())]
        items.sort(key=lambda r: r["priority_score"], reverse=True)
        return items

    def generate_sales_recommendations(self) -> list[dict]:
        """Company-wide next-month demand forecast recommendations."""
        items = [r.to_dict() for r in rules.evaluate_sales_rules(self._sales_trend_signals())]
        items.sort(key=lambda r: r["priority_score"], reverse=True)
        return items

    def generate_all(self) -> list[dict]:
        """Every recommendation across all four types, ranked by priority
        score (highest urgency first) so a manager can work top-down
        regardless of which rule produced each item. Computes each signal
        set once (unlike calling the four `generate_*` methods separately),
        to avoid redoing the same health-score/prediction queries twice.
        """
        customer_signals = self._customer_signals()
        region_signals = self._region_signals()
        sales_signals = self._sales_trend_signals()

        all_recs = (
            rules.evaluate_customer_rules(customer_signals)
            + rules.evaluate_risk_rules(customer_signals)
            + rules.evaluate_regional_rules(region_signals)
            + rules.evaluate_sales_rules(sales_signals)
        )
        items = [r.to_dict() for r in all_recs]
        items.sort(key=lambda r: r["priority_score"], reverse=True)
        return items

    def get_high_priority(self, limit: int = 20) -> list[dict]:
        """Every recommendation (any type) currently banded 'high' priority."""
        items = [r for r in self.generate_all() if r["priority"] == "high"]
        return items[:limit]
