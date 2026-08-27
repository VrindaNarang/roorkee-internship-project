import datetime as dt

from pydantic import BaseModel


class FeatureContribution(BaseModel):
    feature: str
    value: float
    direction: str  # "increases" | "decreases"


class CustomerPrediction(BaseModel):
    college_id: int
    name: str
    institution_type: str
    region: str
    state: str
    purchase_probability: float  # 0-100
    expected_order_value: float  # currency
    expected_revenue: float  # probability-weighted: (purchase_probability/100) * expected_order_value
    confidence_score: float  # 0-100
    prediction_date: dt.datetime
    model_version: str
    probability_explanation: list[FeatureContribution] = []
    expected_value_explanation: list[FeatureContribution] = []


class RetrainResponse(BaseModel):
    status: str
    version: str | None
    classifier_metrics: dict | None
    regressor_metrics: dict | None
    predictions_written: int | None
    message: str
