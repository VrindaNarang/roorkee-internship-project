from pydantic import BaseModel


class Recommendation(BaseModel):
    rule_id: str
    recommendation_type: str  # "customer" | "risk" | "regional" | "sales"
    priority: str  # "high" | "medium" | "low"
    priority_score: float  # 0-100, for ranking within and across types
    title: str
    reason: str
    college_id: int | None = None
    college_name: str | None = None
    region: str | None = None
    metrics: dict = {}
