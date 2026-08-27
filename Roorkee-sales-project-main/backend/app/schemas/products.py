import datetime as dt

from pydantic import BaseModel

from app.schemas.common import PaginationMeta


class ProductListItem(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    unit_price: float
    is_active: bool
    total_revenue: float
    total_quantity_sold: int


class ProductListResponse(BaseModel):
    items: list[ProductListItem]
    meta: PaginationMeta


class ProductDetail(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    unit_price: float
    cost_price: float
    unit_of_measure: str
    is_active: bool
    created_at: dt.datetime
    total_revenue: float
    total_quantity_sold: int
    total_orders: int


class ProductSalesTrendPoint(BaseModel):
    month: str
    revenue: float
    quantity: int


class ProductCategoryOut(BaseModel):
    id: int
    name: str
