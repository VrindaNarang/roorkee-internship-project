import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache import ttl_cache
from app.models import College, Order, OrderItem, Product, ProductCategory
from app.schemas.dashboard import (
    CategoryDistribution,
    DashboardSummary,
    RecentOrder,
    RevenueByState,
    SalesTrendPoint,
    TopCustomer,
    TopProduct,
)
from app.services.date_utils import months_ago_start

REVENUE_EXPR = Order.total_amount

# Dashboard aggregations scan every order — cheap at today's mock-data scale,
# but the pattern that keeps it cheap as data grows. A short TTL keeps the
# dashboard feeling live while absorbing bursts (e.g. the Analytics page
# firing several of these on one render) into a single query.
_CACHE_SECONDS = 30


@ttl_cache(_CACHE_SECONDS)
def get_summary(db: Session) -> DashboardSummary:
    today = dt.date.today()
    month_start = today.replace(day=1)
    prev_month_end = month_start - dt.timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    total_revenue, total_orders = db.query(
        func.coalesce(func.sum(REVENUE_EXPR), 0), func.count(Order.id)
    ).one()

    monthly_revenue = (
        db.query(func.coalesce(func.sum(REVENUE_EXPR), 0))
        .filter(Order.order_date >= month_start, Order.order_date <= today)
        .scalar()
        or 0
    )
    prev_month_revenue = (
        db.query(func.coalesce(func.sum(REVENUE_EXPR), 0))
        .filter(Order.order_date >= prev_month_start, Order.order_date <= prev_month_end)
        .scalar()
        or 0
    )

    active_customers = db.query(func.count(College.id)).filter(College.status == "active").scalar() or 0

    avg_order_value = float(total_revenue) / total_orders if total_orders else 0.0

    if prev_month_revenue:
        growth_pct = round((float(monthly_revenue) - float(prev_month_revenue)) / float(prev_month_revenue) * 100, 2)
    else:
        growth_pct = 0.0

    return DashboardSummary(
        total_revenue=float(total_revenue),
        monthly_revenue=float(monthly_revenue),
        total_orders=total_orders,
        active_customers=active_customers,
        average_order_value=round(avg_order_value, 2),
        revenue_growth_pct=growth_pct,
    )


@ttl_cache(_CACHE_SECONDS)
def get_sales_trend(db: Session, months: int = 12) -> list[SalesTrendPoint]:
    start = months_ago_start(months)
    month_key = func.to_char(Order.order_date, "YYYY-MM")
    rows = (
        db.query(month_key.label("month"), func.sum(REVENUE_EXPR), func.count(Order.id))
        .filter(Order.order_date >= start)
        .group_by("month")
        .order_by("month")
        .all()
    )
    return [SalesTrendPoint(month=row[0], revenue=float(row[1]), orders=row[2]) for row in rows]


@ttl_cache(_CACHE_SECONDS)
def get_revenue_by_state(db: Session) -> list[RevenueByState]:
    rows = (
        db.query(
            College.state,
            College.region,
            func.sum(REVENUE_EXPR),
            func.count(Order.id),
        )
        .join(Order, Order.college_id == College.id)
        .group_by(College.state, College.region)
        .order_by(func.sum(REVENUE_EXPR).desc())
        .all()
    )
    return [
        RevenueByState(state=row[0], region=row[1], revenue=float(row[2]), orders=row[3]) for row in rows
    ]


@ttl_cache(_CACHE_SECONDS)
def get_category_distribution(db: Session) -> list[CategoryDistribution]:
    rows = (
        db.query(
            ProductCategory.name,
            func.sum(OrderItem.line_total),
            func.count(func.distinct(OrderItem.order_id)),
        )
        .join(Product, Product.category_id == ProductCategory.id)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(ProductCategory.name)
        .order_by(func.sum(OrderItem.line_total).desc())
        .all()
    )
    total = sum(float(row[1]) for row in rows) or 1.0
    return [
        CategoryDistribution(
            category=row[0],
            revenue=float(row[1]),
            order_count=row[2],
            pct_of_revenue=round(float(row[1]) / total * 100, 2),
        )
        for row in rows
    ]


@ttl_cache(_CACHE_SECONDS)
def get_top_customers(db: Session, limit: int = 10) -> list[TopCustomer]:
    rows = (
        db.query(
            College.id,
            College.name,
            College.institution_type,
            College.state,
            func.sum(REVENUE_EXPR),
            func.count(Order.id),
            func.max(Order.order_date),
        )
        .join(Order, Order.college_id == College.id)
        .group_by(College.id)
        .order_by(func.sum(REVENUE_EXPR).desc())
        .limit(limit)
        .all()
    )
    return [
        TopCustomer(
            id=row[0],
            name=row[1],
            institution_type=row[2],
            state=row[3],
            total_revenue=float(row[4]),
            total_orders=row[5],
            last_order_date=row[6],
        )
        for row in rows
    ]


@ttl_cache(_CACHE_SECONDS)
def get_top_products(db: Session, limit: int = 10) -> list[TopProduct]:
    rows = (
        db.query(
            Product.id,
            Product.sku,
            Product.name,
            ProductCategory.name,
            func.sum(OrderItem.line_total),
            func.sum(OrderItem.quantity),
        )
        .join(ProductCategory, Product.category_id == ProductCategory.id)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id, ProductCategory.name)
        .order_by(func.sum(OrderItem.line_total).desc())
        .limit(limit)
        .all()
    )
    return [
        TopProduct(
            id=row[0],
            sku=row[1],
            name=row[2],
            category=row[3],
            total_revenue=float(row[4]),
            total_quantity=int(row[5]),
        )
        for row in rows
    ]


@ttl_cache(_CACHE_SECONDS)
def get_recent_orders(db: Session, limit: int = 10) -> list[RecentOrder]:
    rows = (
        db.query(Order, College.name)
        .join(College, Order.college_id == College.id)
        .order_by(Order.order_date.desc(), Order.id.desc())
        .limit(limit)
        .all()
    )
    return [
        RecentOrder(
            id=order.id,
            order_number=order.order_number,
            college_name=college_name,
            order_date=order.order_date,
            status=order.status,
            payment_status=order.payment_status,
            total_amount=float(order.total_amount),
        )
        for order, college_name in rows
    ]
