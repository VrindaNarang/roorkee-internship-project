import datetime as dt

from pydantic import BaseModel


class ContributorOut(BaseModel):
    feature: str
    value: float
    direction: str  # "increases" | "decreases"


class ModelExplanation(BaseModel):
    value: float
    positive_contributors: list[ContributorOut]
    negative_contributors: list[ContributorOut]
    reasons: list[str]
    confidence: float | None = None
    plot_urls: dict[str, str] = {}


class CustomerExplanation(BaseModel):
    college_id: int
    name: str
    health_score: ModelExplanation | None
    purchase_probability: ModelExplanation | None
    expected_order_value: ModelExplanation | None
    overall_confidence: float | None
    generated_at: dt.datetime | None


class GlobalFeatureRow(BaseModel):
    feature: str
    mean_abs_contribution: float
    rank: int


class GlobalModelExplanation(BaseModel):
    top_features: list[GlobalFeatureRow]
    summary_text: str
    plot_urls: dict[str, str] = {}


class GlobalExplanation(BaseModel):
    generated_at: dt.datetime
    model_version: str
    purchase_probability: GlobalModelExplanation
    expected_order_value: GlobalModelExplanation


class TopFeaturesResponse(BaseModel):
    model: str
    top_features: list[GlobalFeatureRow]


class ModelSummaryEntry(BaseModel):
    model_name: str
    model_type: str
    version: str
    trained_at: dt.datetime
    metrics: dict


class ModelSummaryResponse(BaseModel):
    purchase_propensity_classifier: ModelSummaryEntry | None
    expected_order_value_regressor: ModelSummaryEntry | None
    customer_health_score: dict
