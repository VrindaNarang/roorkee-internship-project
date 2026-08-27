import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.predictions import CustomerPrediction
from app.services import predictions_service

logger = logging.getLogger(__name__)
router = APIRouter()

# NOTE: `GET /feature-importance` used to live here but was removed
# (Milestone 11) — it read `global_feature_importance.json` with the schema
# from before Milestone 8 rewrote that file's shape (per-model breakdown),
# so it had been silently 500ing since Milestone 8 shipped. `GET
# /explain/global` and `GET /explain/top-features` (see explain.py) already
# fully supersede it with the current file shape.


@router.get("/customers", response_model=list[CustomerPrediction])
def list_customer_predictions(
    state: str | None = None,
    institution_type: str | None = Query(None, pattern="^(government|private)$"),
    min_probability: float | None = Query(None, ge=0, le=100),
    min_expected_revenue: float | None = Query(None, ge=0),
    db: Session = Depends(get_db),
) -> list[CustomerPrediction]:
    """All customers with a current prediction, ranked by expected revenue.

    Filterable by state, customer type, minimum purchase probability (0-100),
    and minimum expected revenue — matches the Sales Opportunities page's
    filter controls.
    """
    return predictions_service.list_predictions(
        db,
        state=state,
        institution_type=institution_type,
        min_probability=min_probability,
        min_expected_revenue=min_expected_revenue,
    )


@router.get("/high-probability", response_model=list[CustomerPrediction])
def list_high_probability_customers(
    min_probability: float = Query(70.0, ge=0, le=100),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[CustomerPrediction]:
    """Customers most likely to purchase in the next 30 days, best first."""
    return predictions_service.get_high_probability(db, min_probability=min_probability, limit=limit)


@router.get("/top-opportunities", response_model=list[CustomerPrediction])
def list_top_opportunities(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
) -> list[CustomerPrediction]:
    """Customers ranked by expected revenue (probability x expected order
    value) — the single list a sales manager should work down first.
    """
    return predictions_service.get_top_opportunities(db, limit=limit)


@router.get("/customer/{customer_id}", response_model=CustomerPrediction)
def get_customer_prediction(customer_id: int, db: Session = Depends(get_db)) -> CustomerPrediction:
    prediction = predictions_service.get_for_customer(db, customer_id)
    if prediction is None:
        raise HTTPException(
            status_code=404,
            detail="No prediction available for this customer yet — POST /ml/retrain first",
        )
    return prediction
