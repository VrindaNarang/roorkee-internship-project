import json
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.predictions import CustomerPrediction, FeatureContribution

logger = logging.getLogger(__name__)

# One SELECT DISTINCT ON, joined against colleges, gets exactly the latest
# `purchase_probability` row and the latest `expected_order_value` row per
# college in a single round trip — `predict.py` writes both every batch run,
# each carrying its own SHAP explanation.
_LATEST_PREDICTIONS_SQL = """
    SELECT DISTINCT ON (p.college_id, p.prediction_type)
        p.college_id, c.name, c.institution_type, c.region, c.state,
        p.prediction_type, p.predicted_value, p.probability, p.prediction_date,
        p.model_version, p.shap_explanation
    FROM predictions p
    JOIN colleges c ON c.id = p.college_id
    ORDER BY p.college_id, p.prediction_type, p.prediction_date DESC
"""


def _parse_explanation(raw: object) -> list[FeatureContribution]:
    """`shap_explanation` is written by `ml/prediction/predict.py` as
    `{"contributors": [...], "positive_contributors": [...],
    "negative_contributors": [...], "reasons": [...]}` (see
    `explainability/shap_service.py`). This flattens it back to the simple
    top-N contributor list this schema's callers expect.
    """
    if not raw:
        return []
    payload = raw if isinstance(raw, (dict, list)) else json.loads(raw)
    contributors = payload["contributors"] if isinstance(payload, dict) else payload
    return [FeatureContribution(**item) for item in contributors]


def _fetch_latest_predictions(db: Session) -> list[CustomerPrediction]:
    rows = db.execute(text(_LATEST_PREDICTIONS_SQL)).all()

    by_college: dict[int, dict] = {}
    for row in rows:
        entry = by_college.setdefault(
            row.college_id,
            {
                "college_id": row.college_id,
                "name": row.name,
                "institution_type": row.institution_type,
                "region": row.region,
                "state": row.state,
                "probability": None,
                "expected_order_value": None,
                "prediction_date": row.prediction_date,
                "model_version": row.model_version,
                "probability_explanation": [],
                "expected_value_explanation": [],
            },
        )
        if row.prediction_type == "purchase_probability":
            entry["probability"] = row.probability
            entry["prediction_date"] = row.prediction_date
            entry["model_version"] = row.model_version
            entry["probability_explanation"] = _parse_explanation(row.shap_explanation)
        elif row.prediction_type == "expected_order_value":
            entry["expected_order_value"] = row.predicted_value
            entry["expected_value_explanation"] = _parse_explanation(row.shap_explanation)

    predictions: list[CustomerPrediction] = []
    for entry in by_college.values():
        probability = entry["probability"]
        expected_value = entry["expected_order_value"]
        # A college needs both halves of a scoring run to be usable — skip
        # any partial row rather than guessing a value.
        if probability is None or expected_value is None:
            continue
        confidence = abs(probability - 0.5) * 2
        predictions.append(
            CustomerPrediction(
                college_id=entry["college_id"],
                name=entry["name"],
                institution_type=entry["institution_type"],
                region=entry["region"],
                state=entry["state"],
                purchase_probability=round(probability * 100, 2),
                expected_order_value=round(expected_value, 2),
                expected_revenue=round(probability * expected_value, 2),
                confidence_score=round(confidence * 100, 2),
                prediction_date=entry["prediction_date"],
                model_version=entry["model_version"],
                probability_explanation=entry["probability_explanation"],
                expected_value_explanation=entry["expected_value_explanation"],
            )
        )
    return predictions


def list_predictions(
    db: Session,
    *,
    state: str | None = None,
    institution_type: str | None = None,
    min_probability: float | None = None,
    min_expected_revenue: float | None = None,
) -> list[CustomerPrediction]:
    predictions = _fetch_latest_predictions(db)

    if state:
        predictions = [p for p in predictions if p.state == state]
    if institution_type:
        predictions = [p for p in predictions if p.institution_type == institution_type]
    if min_probability is not None:
        predictions = [p for p in predictions if p.purchase_probability >= min_probability]
    if min_expected_revenue is not None:
        predictions = [p for p in predictions if p.expected_revenue >= min_expected_revenue]

    predictions.sort(key=lambda p: p.expected_revenue, reverse=True)
    return predictions


def get_for_customer(db: Session, college_id: int) -> CustomerPrediction | None:
    for prediction in _fetch_latest_predictions(db):
        if prediction.college_id == college_id:
            return prediction
    return None


def get_high_probability(db: Session, *, min_probability: float = 70.0, limit: int = 20) -> list[CustomerPrediction]:
    predictions = [p for p in _fetch_latest_predictions(db) if p.purchase_probability >= min_probability]
    predictions.sort(key=lambda p: p.purchase_probability, reverse=True)
    return predictions[:limit]


def get_top_opportunities(db: Session, *, limit: int = 20) -> list[CustomerPrediction]:
    predictions = _fetch_latest_predictions(db)
    predictions.sort(key=lambda p: p.expected_revenue, reverse=True)
    return predictions[:limit]
