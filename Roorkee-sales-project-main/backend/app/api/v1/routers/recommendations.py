import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.recommendation_engine.recommendation_service import RecommendationService
from app.schemas.recommendations import Recommendation

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[Recommendation])
def list_all_recommendations(db: Session = Depends(get_db)) -> list[Recommendation]:
    """Every recommendation across all four types (customer, risk, regional,
    sales), ranked by priority score — highest urgency first.
    """
    return RecommendationService(db).generate_all()


@router.get("/customers", response_model=list[Recommendation])
def list_customer_recommendations(db: Session = Depends(get_db)) -> list[Recommendation]:
    """'Contact this week' recommendations, one per customer worth proactive
    outreach right now (high purchase probability + a healthy account).
    """
    return RecommendationService(db).generate_customer_recommendations()


@router.get("/regions", response_model=list[Recommendation])
def list_regional_recommendations(db: Session = Depends(get_db)) -> list[Recommendation]:
    """Regional revenue swings — declines worth a marketing push, or growth
    worth reinforcing with more sales coverage.
    """
    return RecommendationService(db).generate_regional_recommendations()


@router.get("/high-priority", response_model=list[Recommendation])
def list_high_priority_recommendations(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
) -> list[Recommendation]:
    """Every recommendation (any type) currently banded 'high' priority."""
    return RecommendationService(db).get_high_priority(limit=limit)


@router.get("/risk", response_model=list[Recommendation])
def list_risk_recommendations(db: Session = Depends(get_db)) -> list[Recommendation]:
    """Customers who need a proactive follow-up: a dormant account (no
    purchase in 180+ days) or a health score that has dropped below 40.
    """
    return RecommendationService(db).generate_risk_recommendations()
