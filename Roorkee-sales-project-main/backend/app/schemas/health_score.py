import datetime as dt

from pydantic import BaseModel


class CustomerHealthListItem(BaseModel):
    college_id: int
    name: str
    institution_type: str
    region: str
    state: str
    health_score: float
    health_status: str
    previous_health_score: float | None
    health_trend: str
    last_updated: dt.datetime


class ComponentScoreOut(BaseModel):
    raw_value: float
    normalized_score: float
    weight: float
    contribution: float


class CustomerHealthDetail(CustomerHealthListItem):
    rfm_recency: float
    rfm_frequency: float
    rfm_monetary: float
    model_version: str
    component_breakdown: dict[str, ComponentScoreOut]


class RecalculateResponse(BaseModel):
    scored_at: dt.datetime
    total_customers: int
    healthy: int
    at_risk: int
    critical: int
    model_version: str
