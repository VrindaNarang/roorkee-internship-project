import datetime as dt

from pydantic import BaseModel

from app.schemas.common import PaginationMeta


class CustomerListItem(BaseModel):
    id: int
    name: str
    institution_type: str
    region: str
    state: str
    city: str
    status: str
    total_orders: int
    total_revenue: float
    last_order_date: dt.date | None


class CustomerListResponse(BaseModel):
    items: list[CustomerListItem]
    meta: PaginationMeta


class CustomerDetail(BaseModel):
    id: int
    name: str
    institution_type: str
    region: str
    state: str
    city: str
    address: str
    contact_name: str
    contact_email: str
    contact_phone: str
    onboarded_date: dt.date
    status: str
    total_orders: int
    total_revenue: float
    average_order_value: float
    last_order_date: dt.date | None


class CustomerOrderItem(BaseModel):
    id: int
    order_number: str
    order_date: dt.date
    status: str
    payment_status: str
    total_amount: float
    item_count: int
