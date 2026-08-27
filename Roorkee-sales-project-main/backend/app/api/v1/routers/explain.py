import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.explainability import (
    CustomerExplanation,
    GlobalExplanation,
    ModelSummaryResponse,
    TopFeaturesResponse,
)
from app.services import explainability_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/customer/{customer_id}", response_model=CustomerExplanation)
def explain_customer(customer_id: int, db: Session = Depends(get_db)) -> CustomerExplanation:
    """Full local explanation for one customer: health score, purchase
    probability, and expected order value, each with positive/negative
    contributors and plain-English reasons.
    """
    explanation = explainability_service.get_customer_explanation(db, customer_id)
    if explanation is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return explanation


@router.get("/global", response_model=GlobalExplanation)
def explain_global(db: Session = Depends(get_db)) -> GlobalExplanation:
    """Global explainability: what drives purchase probability and expected
    order value across the whole current customer base, plus summary/bar
    plot URLs.
    """
    explanation = explainability_service.get_global_explanation(db)
    if explanation is None:
        raise HTTPException(
            status_code=404, detail="No global explanation available yet — POST /ml/retrain first"
        )
    return explanation


@router.get("/top-features", response_model=TopFeaturesResponse)
def explain_top_features(
    model: str = Query("purchase_probability", pattern="^(purchase_probability|expected_order_value)$"),
    limit: int = Query(10, ge=1, le=20),
) -> TopFeaturesResponse:
    """Ranked global feature-importance list for one model."""
    result = explainability_service.get_top_features(model=model, limit=limit)
    if result is None:
        raise HTTPException(
            status_code=404, detail="No feature-importance data available yet — POST /ml/retrain first"
        )
    return result


@router.get("/model-summary", response_model=ModelSummaryResponse)
def explain_model_summary(db: Session = Depends(get_db)) -> ModelSummaryResponse:
    """Metadata + evaluation metrics for every model behind the dashboard's
    predictions — the two XGBoost models and the health-score formula.
    """
    return explainability_service.get_model_summary(db)
