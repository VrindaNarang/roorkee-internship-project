"""Orchestrates the Customer Health Scoring engine: pulls raw order/college
data from Postgres, computes the ten weighted factors per customer via
`scoring.py`, persists a new scoring run, and serves the read queries the
API layer needs.

Kept as a service class (not free functions) so it can hold a single DB
session across the whole recalculation run and so API routers stay thin —
"separate business logic from API routes" per this milestone's brief.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import ttl_cache
from app.health_score import scoring
from app.health_score.config import MODEL_VERSION
from app.models import College, CustomerHealthScore, Order

logger = logging.getLogger(__name__)

RECENT_WINDOW_DAYS = 90  # window used for "revenue generated" and growth-trend comparison
PAYMENT_DELAY_WINDOW_DAYS = 365  # only recent orders count toward current payment-reliability
FACTORS_CACHE_SECONDS = 30  # compute_factors() scans every order for every college — worth a short cache


@dataclass
class _OrderRow:
    college_id: int
    order_date: date
    total_amount: float
    payment_due_date: date | None
    payment_received_date: date | None


@dataclass
class RecalculateSummary:
    scored_at: datetime
    total_customers: int
    healthy: int
    at_risk: int
    critical: int
    model_version: str


class HealthScoreService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Factor computation
    # ------------------------------------------------------------------
    def _fetch_orders_by_college(self) -> dict[int, list[_OrderRow]]:
        rows = self.db.execute(
            select(
                Order.college_id,
                Order.order_date,
                Order.total_amount,
                Order.payment_due_date,
                Order.payment_received_date,
            )
        ).all()

        by_college: dict[int, list[_OrderRow]] = defaultdict(list)
        for college_id, order_date, total_amount, due_date, received_date in rows:
            by_college[college_id].append(
                _OrderRow(
                    college_id=college_id,
                    order_date=order_date,
                    total_amount=float(total_amount),
                    payment_due_date=due_date,
                    payment_received_date=received_date,
                )
            )
        return by_college

    def _payment_delay_days(self, orders: list[_OrderRow], reference_date: date) -> float:
        """Average payment delay over a **recent rolling window** only.

        Deliberately not computed over full order history: an order from
        years ago that was never marked paid would otherwise inflate "delay"
        indefinitely as `reference_date` keeps marching forward, even though
        that ancient balance says nothing about the customer's *current*
        payment reliability. Recent behavior is what should drive a live
        health score.
        """
        window_start = reference_date - timedelta(days=PAYMENT_DELAY_WINDOW_DAYS)
        delays: list[float] = []
        for o in orders:
            if o.order_date < window_start:
                continue
            if o.payment_received_date is not None:
                delays.append((o.payment_received_date - o.payment_due_date).days)
            elif o.payment_due_date is not None and reference_date > o.payment_due_date:
                delays.append((reference_date - o.payment_due_date).days)
        return statistics.mean(delays) if delays else 0.0

    def _order_consistency(self, order_dates: list[date]) -> float:
        if len(order_dates) < 2:
            return 0.5  # neutral default for customers with < 2 orders — nothing to measure cadence from
        gaps = [
            (order_dates[i] - order_dates[i - 1]).days for i in range(1, len(order_dates))
        ]
        mean_gap = statistics.mean(gaps)
        if mean_gap == 0 or len(gaps) < 2:
            return 0.5
        stdev_gap = statistics.stdev(gaps)
        cv = stdev_gap / mean_gap
        return 1 / (1 + cv)

    def _revenue_growth(self, orders: list[_OrderRow], reference_date: date) -> float:
        recent_start = reference_date - timedelta(days=RECENT_WINDOW_DAYS)
        prior_start = reference_date - timedelta(days=2 * RECENT_WINDOW_DAYS)

        recent = sum(o.total_amount for o in orders if o.order_date > recent_start)
        prior = sum(o.total_amount for o in orders if prior_start < o.order_date <= recent_start)

        if prior == 0:
            return 0.0
        return (recent - prior) / prior * 100

    @ttl_cache(FACTORS_CACHE_SECONDS)
    def compute_factors(self, reference_date: date | None = None) -> list[scoring.CustomerFactors]:
        reference_date = reference_date or datetime.now(timezone.utc).date()
        colleges = self.db.execute(select(College)).scalars().all()
        orders_by_college = self._fetch_orders_by_college()

        factors: list[scoring.CustomerFactors] = []
        for college in colleges:
            orders = sorted(orders_by_college.get(college.id, []), key=lambda o: o.order_date)
            total_orders = len(orders)
            order_dates = [o.order_date for o in orders]

            if total_orders:
                clv = sum(o.total_amount for o in orders)
                aov = clv / total_orders
                last_order_date = order_dates[-1]
                days_since_last_purchase = (reference_date - last_order_date).days
                active_months = len({(d.year, d.month) for d in order_dates})
                purchase_frequency = total_orders / active_months if active_months else 0.0
            else:
                clv = 0.0
                aov = 0.0
                days_since_last_purchase = (reference_date - college.onboarded_date).days
                active_months = 0
                purchase_frequency = 0.0

            revenue_generated = sum(
                o.total_amount
                for o in orders
                if o.order_date > reference_date - timedelta(days=RECENT_WINDOW_DAYS)
            )

            factors.append(
                scoring.CustomerFactors(
                    college_id=college.id,
                    days_since_last_purchase=float(days_since_last_purchase),
                    purchase_frequency=purchase_frequency,
                    customer_lifetime_value=clv,
                    average_order_value=aov,
                    average_payment_delay=self._payment_delay_days(orders, reference_date),
                    number_of_orders=float(total_orders),
                    revenue_generated=revenue_generated,
                    seasonal_purchasing_consistency=self._order_consistency(order_dates),
                    months_active=float(active_months),
                    order_growth_trend=self._revenue_growth(orders, reference_date),
                )
            )

        logger.info("Computed health-score factors for %d customers", len(factors))
        return factors

    # ------------------------------------------------------------------
    # Recalculation (write path)
    # ------------------------------------------------------------------
    def recalculate(self) -> RecalculateSummary:
        """Runs a full scoring pass over every customer and appends one new
        row per customer to `customer_health_scores`. This is the function
        to call whenever new sales data is imported (see module docstring) —
        today that means the manual `POST /customers/health` endpoint; once
        a CSV-import job exists, it should call this at the end of a
        successful import.
        """
        scored_at = datetime.now(timezone.utc)
        factors = self.compute_factors(scored_at.date())
        results = scoring.score_all(factors)

        counts = {"healthy": 0, "at_risk": 0, "critical": 0}
        for result in results:
            counts[result.health_status] += 1
            self.db.add(
                CustomerHealthScore(
                    college_id=result.college_id,
                    score_date=scored_at,
                    health_score=result.health_score,
                    health_status=result.health_status,
                    rfm_recency=result.rfm_recency,
                    rfm_frequency=result.rfm_frequency,
                    rfm_monetary=result.rfm_monetary,
                    component_breakdown=result.breakdown_as_dict(),
                    model_version=MODEL_VERSION,
                )
            )
        self.db.commit()

        summary = RecalculateSummary(
            scored_at=scored_at,
            total_customers=len(results),
            healthy=counts["healthy"],
            at_risk=counts["at_risk"],
            critical=counts["critical"],
            model_version=MODEL_VERSION,
        )
        logger.info(
            "Health score recalculation complete: %d customers scored (healthy=%d, at_risk=%d, critical=%d)",
            summary.total_customers,
            summary.healthy,
            summary.at_risk,
            summary.critical,
        )
        return summary

    # ------------------------------------------------------------------
    # Read path — latest score (+ trend) per customer
    # ------------------------------------------------------------------
    def _latest_two_scores_by_college(self) -> dict[int, list[CustomerHealthScore]]:
        ranked = (
            select(
                CustomerHealthScore,
                func.row_number()
                .over(
                    partition_by=CustomerHealthScore.college_id,
                    order_by=CustomerHealthScore.score_date.desc(),
                )
                .label("rn"),
            )
        ).subquery()

        rows = (
            self.db.execute(
                select(CustomerHealthScore)
                .select_from(ranked)
                .join(CustomerHealthScore, CustomerHealthScore.id == ranked.c.id)
                .where(ranked.c.rn <= 2)
                .order_by(CustomerHealthScore.college_id, ranked.c.rn)
            )
            .scalars()
            .all()
        )

        by_college: dict[int, list[CustomerHealthScore]] = defaultdict(list)
        for row in rows:
            by_college[row.college_id].append(row)
        return by_college

    @staticmethod
    def _trend(latest: CustomerHealthScore, previous: CustomerHealthScore | None) -> tuple[str, float | None]:
        if previous is None:
            return "new", None
        delta = latest.health_score - previous.health_score
        if delta > 1.0:
            return "improving", previous.health_score
        if delta < -1.0:
            return "declining", previous.health_score
        return "stable", previous.health_score

    def list_latest(self, status: str | None = None) -> list[dict]:
        by_college = self._latest_two_scores_by_college()
        colleges = {c.id: c for c in self.db.execute(select(College)).scalars().all()}

        items = []
        for college_id, scores in by_college.items():
            latest, previous = scores[0], scores[1] if len(scores) > 1 else None
            if status and latest.health_status != status:
                continue
            trend, previous_score = self._trend(latest, previous)
            college = colleges.get(college_id)
            if college is None:
                continue
            items.append(
                {
                    "college_id": college_id,
                    "name": college.name,
                    "institution_type": college.institution_type,
                    "region": college.region,
                    "state": college.state,
                    "health_score": latest.health_score,
                    "health_status": latest.health_status,
                    "previous_health_score": previous_score,
                    "health_trend": trend,
                    "last_updated": latest.score_date,
                }
            )
        return items

    def get_for_customer(self, college_id: int) -> dict | None:
        rows = (
            self.db.execute(
                select(CustomerHealthScore)
                .where(CustomerHealthScore.college_id == college_id)
                .order_by(CustomerHealthScore.score_date.desc())
                .limit(2)
            )
            .scalars()
            .all()
        )
        if not rows:
            return None
        latest = rows[0]
        previous = rows[1] if len(rows) > 1 else None
        trend, previous_score = self._trend(latest, previous)

        college = self.db.get(College, college_id)
        return {
            "college_id": college_id,
            "name": college.name if college else None,
            "institution_type": college.institution_type if college else None,
            "region": college.region if college else None,
            "state": college.state if college else None,
            "health_score": latest.health_score,
            "health_status": latest.health_status,
            "previous_health_score": previous_score,
            "health_trend": trend,
            "last_updated": latest.score_date,
            "rfm_recency": latest.rfm_recency,
            "rfm_frequency": latest.rfm_frequency,
            "rfm_monetary": latest.rfm_monetary,
            "model_version": latest.model_version,
            "component_breakdown": latest.component_breakdown,
        }
