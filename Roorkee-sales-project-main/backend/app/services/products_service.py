from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache import ttl_cache
from app.models import Order, OrderItem, Product, ProductCategory
from app.schemas.common import PaginationMeta
from app.schemas.products import (
    ProductCategoryOut,
    ProductDetail,
    ProductListItem,
    ProductListResponse,
    ProductSalesTrendPoint,
)
from app.services.date_utils import months_ago_start

_CACHE_SECONDS = 30


@ttl_cache(_CACHE_SECONDS)
def list_products(
    db: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ProductListResponse:
    revenue_col = func.coalesce(func.sum(OrderItem.line_total), 0).label("total_revenue")
    quantity_col = func.coalesce(func.sum(OrderItem.quantity), 0).label("total_quantity")

    query = (
        db.query(Product, ProductCategory.name, revenue_col, quantity_col)
        .join(ProductCategory, Product.category_id == ProductCategory.id)
        .outerjoin(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id, ProductCategory.name)
    )

    if search:
        like = f"%{search.strip()}%"
        query = query.filter(Product.name.ilike(like) | Product.sku.ilike(like))
    if category:
        query = query.filter(ProductCategory.name == category)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(max(1, page), total_pages)

    rows = (
        query.order_by(revenue_col.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )

    items = [
        ProductListItem(
            id=product.id,
            sku=product.sku,
            name=product.name,
            category=category_name,
            unit_price=float(product.unit_price),
            is_active=product.is_active,
            total_revenue=float(total_revenue),
            total_quantity_sold=int(total_quantity),
        )
        for product, category_name, total_revenue, total_quantity in rows
    ]

    return ProductListResponse(
        items=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@ttl_cache(_CACHE_SECONDS)
def get_categories(db: Session) -> list[ProductCategoryOut]:
    rows = db.query(ProductCategory).order_by(ProductCategory.name).all()
    return [ProductCategoryOut(id=row.id, name=row.name) for row in rows]


def get_product_detail(db: Session, product_id: int) -> ProductDetail | None:
    row = (
        db.query(Product, ProductCategory.name)
        .join(ProductCategory, Product.category_id == ProductCategory.id)
        .filter(Product.id == product_id)
        .first()
    )
    if row is None:
        return None
    product, category_name = row

    total_revenue, total_quantity, total_orders = (
        db.query(
            func.coalesce(func.sum(OrderItem.line_total), 0),
            func.coalesce(func.sum(OrderItem.quantity), 0),
            func.count(func.distinct(OrderItem.order_id)),
        )
        .filter(OrderItem.product_id == product_id)
        .one()
    )

    return ProductDetail(
        id=product.id,
        sku=product.sku,
        name=product.name,
        category=category_name,
        unit_price=float(product.unit_price),
        cost_price=float(product.cost_price),
        unit_of_measure=product.unit_of_measure,
        is_active=product.is_active,
        created_at=product.created_at,
        total_revenue=float(total_revenue),
        total_quantity_sold=int(total_quantity),
        total_orders=total_orders,
    )


def get_product_sales_trend(db: Session, product_id: int, months: int = 12) -> list[ProductSalesTrendPoint]:
    start = months_ago_start(months)
    month_key = func.to_char(Order.order_date, "YYYY-MM")
    rows = (
        db.query(month_key.label("month"), func.sum(OrderItem.line_total), func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(OrderItem.product_id == product_id, Order.order_date >= start)
        .group_by("month")
        .order_by("month")
        .all()
    )
    return [
        ProductSalesTrendPoint(month=row[0], revenue=float(row[1]), quantity=int(row[2])) for row in rows
    ]
