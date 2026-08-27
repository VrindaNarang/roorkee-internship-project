from pydantic import BaseModel


class InstitutionTypeBreakdown(BaseModel):
    institution_type: str
    customer_count: int
    revenue: float
    avg_order_value: float


class RegionPerformance(BaseModel):
    region: str
    revenue: float
    orders: int
    customer_count: int
    avg_order_value: float


class CustomerInsights(BaseModel):
    institution_type_breakdown: list[InstitutionTypeBreakdown]
    new_customers_last_90_days: int
    at_risk_customers: int
    repeat_customer_pct: float
