import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache import ttl_cache
from app.models import College, Order
from app.schemas.analytics import CustomerInsights, InstitutionTypeBreakdown, RegionPerformance

AT_RISK_DAYS = 120
NEW_CUSTOMER_DAYS = 90
_CACHE_SECONDS = 30


@ttl_cache(_CACHE_SECONDS)
def get_region_performance(db: Session) -> list[RegionPerformance]:
    revenue_col = func.coalesce(func.sum(Order.total_amount), 0)
    orders_col = func.count(Order.id)
    customers_col = func.count(func.distinct(College.id))

    rows = (
        db.query(College.region, revenue_col, orders_col, customers_col)
        .join(Order, Order.college_id == College.id)
        .group_by(College.region)
        .order_by(revenue_col.desc())
        .all()
    )
    return [
        RegionPerformance(
            region=row[0],
            revenue=float(row[1]),
            orders=row[2],
            customer_count=row[3],
            avg_order_value=round(float(row[1]) / row[2], 2) if row[2] else 0.0,
        )
        for row in rows
    ]


@ttl_cache(_CACHE_SECONDS)
def get_customer_insights(db: Session) -> CustomerInsights:
    revenue_col = func.coalesce(func.sum(Order.total_amount), 0)
    orders_col = func.count(Order.id)
    customers_col = func.count(func.distinct(College.id))

    rows = (
        db.query(College.institution_type, customers_col, revenue_col, orders_col)
        .join(Order, Order.college_id == College.id)
        .group_by(College.institution_type)
        .all()
    )
    breakdown = [
        InstitutionTypeBreakdown(
            institution_type=row[0],
            customer_count=row[1],
            revenue=float(row[2]),
            avg_order_value=round(float(row[2]) / row[3], 2) if row[3] else 0.0,
        )
        for row in rows
    ]

    today = dt.date.today()
    new_customers = (
        db.query(func.count(College.id))
        .filter(College.onboarded_date >= today - dt.timedelta(days=NEW_CUSTOMER_DAYS))
        .scalar()
        or 0
    )

    # Simple recency-based business rule (not a predictive model): an
    # "active"-flagged college with no order in the last AT_RISK_DAYS days.
    last_order_subq = (
        db.query(Order.college_id, func.max(Order.order_date).label("last_order_date"))
        .group_by(Order.college_id)
        .subquery()
    )
    at_risk = (
        db.query(func.count(College.id))
        .outerjoin(last_order_subq, last_order_subq.c.college_id == College.id)
        .filter(College.status == "active")
        .filter(
            (last_order_subq.c.last_order_date == None)  # noqa: E711
            | (last_order_subq.c.last_order_date < today - dt.timedelta(days=AT_RISK_DAYS))
        )
        .scalar()
        or 0
    )

    total_customers = db.query(func.count(College.id)).scalar() or 0
    repeat_customers = (
        db.query(func.count())
        .select_from(
            db.query(Order.college_id)
            .group_by(Order.college_id)
            .having(func.count(Order.id) > 1)
            .subquery()
        )
        .scalar()
        or 0
    )
    repeat_pct = round(repeat_customers / total_customers * 100, 2) if total_customers else 0.0

    return CustomerInsights(
        institution_type_breakdown=breakdown,
        new_customers_last_90_days=new_customers,
        at_risk_customers=at_risk,
        repeat_customer_pct=repeat_pct,
    )
