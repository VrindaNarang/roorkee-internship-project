import datetime as dt

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_revenue: float
    monthly_revenue: float
    total_orders: int
    active_customers: int
    average_order_value: float
    revenue_growth_pct: float
    currency: str = "INR"


class SalesTrendPoint(BaseModel):
    month: str
    revenue: float
    orders: int


class RevenueByState(BaseModel):
    state: str
    region: str
    revenue: float
    orders: int


class CategoryDistribution(BaseModel):
    category: str
    revenue: float
    order_count: int
    pct_of_revenue: float


class TopCustomer(BaseModel):
    id: int
    name: str
    institution_type: str
    state: str
    total_revenue: float
    total_orders: int
    last_order_date: dt.date | None


class TopProduct(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    total_revenue: float
    total_quantity: int


class RecentOrder(BaseModel):
    id: int
    order_number: str
    college_name: str
    order_date: dt.date
    status: str
    payment_status: str
    total_amount: float
