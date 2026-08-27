import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import CustomerInsights, RegionPerformance
from app.schemas.dashboard import RevenueByState, SalesTrendPoint
from app.services import analytics_service, dashboard_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sales-trend", response_model=list[SalesTrendPoint])
def get_sales_trend(
    months: int = Query(12, ge=1, le=36), db: Session = Depends(get_db)
) -> list[SalesTrendPoint]:
    return dashboard_service.get_sales_trend(db, months=months)


@router.get("/revenue-by-state", response_model=list[RevenueByState])
def get_revenue_by_state(db: Session = Depends(get_db)) -> list[RevenueByState]:
    return dashboard_service.get_revenue_by_state(db)


@router.get("/region-performance", response_model=list[RegionPerformance])
def get_region_performance(db: Session = Depends(get_db)) -> list[RegionPerformance]:
    return analytics_service.get_region_performance(db)


@router.get("/customer-insights", response_model=CustomerInsights)
def get_customer_insights(db: Session = Depends(get_db)) -> CustomerInsights:
    return analytics_service.get_customer_insights(db)
