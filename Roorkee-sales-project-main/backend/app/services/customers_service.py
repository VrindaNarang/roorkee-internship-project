from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import College, Order, OrderItem
from app.schemas.common import PaginationMeta
from app.schemas.customers import (
    CustomerDetail,
    CustomerListItem,
    CustomerListResponse,
    CustomerOrderItem,
)


def list_customers(
    db: Session,
    *,
    search: str | None = None,
    state: str | None = None,
    institution_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> CustomerListResponse:
    revenue_col = func.coalesce(func.sum(Order.total_amount), 0).label("total_revenue")
    orders_col = func.count(Order.id).label("total_orders")
    last_order_col = func.max(Order.order_date).label("last_order_date")

    query = (
        db.query(
            College,
            revenue_col,
            orders_col,
            last_order_col,
        )
        .outerjoin(Order, Order.college_id == College.id)
        .group_by(College.id)
    )

    if search:
        like = f"%{search.strip()}%"
        query = query.filter(or_(College.name.ilike(like), College.city.ilike(like)))
    if state:
        query = query.filter(College.state == state)
    if institution_type:
        query = query.filter(College.institution_type == institution_type)
    if status:
        query = query.filter(College.status == status)

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(max(1, page), total_pages)

    rows = (
        query.order_by(revenue_col.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )

    items = [
        CustomerListItem(
            id=college.id,
            name=college.name,
            institution_type=college.institution_type,
            region=college.region,
            state=college.state,
            city=college.city,
            status=college.status,
            total_orders=total_orders,
            total_revenue=float(total_revenue),
            last_order_date=last_order_date,
        )
        for college, total_revenue, total_orders, last_order_date in rows
    ]

    return CustomerListResponse(
        items=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


def get_distinct_states(db: Session) -> list[str]:
    rows = db.query(College.state).distinct().order_by(College.state).all()
    return [row[0] for row in rows]


def get_customer_detail(db: Session, college_id: int) -> CustomerDetail | None:
    college = db.query(College).filter(College.id == college_id).first()
    if college is None:
        return None

    total_revenue, total_orders, last_order_date = (
        db.query(
            func.coalesce(func.sum(Order.total_amount), 0),
            func.count(Order.id),
            func.max(Order.order_date),
        )
        .filter(Order.college_id == college_id)
        .one()
    )

    avg_order_value = float(total_revenue) / total_orders if total_orders else 0.0

    return CustomerDetail(
        id=college.id,
        name=college.name,
        institution_type=college.institution_type,
        region=college.region,
        state=college.state,
        city=college.city,
        address=college.address,
        contact_name=college.contact_name,
        contact_email=college.contact_email,
        contact_phone=college.contact_phone,
        onboarded_date=college.onboarded_date,
        status=college.status,
        total_orders=total_orders,
        total_revenue=float(total_revenue),
        average_order_value=round(avg_order_value, 2),
        last_order_date=last_order_date,
    )


def get_customer_orders(db: Session, college_id: int, limit: int = 50) -> list[CustomerOrderItem]:
    item_count_col = func.count(OrderItem.id).label("item_count")
    rows = (
        db.query(Order, item_count_col)
        .outerjoin(OrderItem, OrderItem.order_id == Order.id)
        .filter(Order.college_id == college_id)
        .group_by(Order.id)
        .order_by(Order.order_date.desc())
        .limit(limit)
        .all()
    )
    return [
        CustomerOrderItem(
            id=order.id,
            order_number=order.order_number,
            order_date=order.order_date,
            status=order.status,
            payment_status=order.payment_status,
            total_amount=float(order.total_amount),
            item_count=item_count,
        )
        for order, item_count in rows
    ]
