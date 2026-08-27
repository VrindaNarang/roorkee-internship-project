import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import (
    CategoryDistribution,
    DashboardSummary,
    RecentOrder,
    RevenueByState,
    SalesTrendPoint,
    TopCustomer,
    TopProduct,
)
from app.services import dashboard_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    return dashboard_service.get_summary(db)


@router.get("/sales-trend", response_model=list[SalesTrendPoint])
def get_sales_trend(
    months: int = Query(12, ge=1, le=36), db: Session = Depends(get_db)
) -> list[SalesTrendPoint]:
    return dashboard_service.get_sales_trend(db, months=months)


@router.get("/revenue-by-state", response_model=list[RevenueByState])
def get_revenue_by_state(db: Session = Depends(get_db)) -> list[RevenueByState]:
    return dashboard_service.get_revenue_by_state(db)


@router.get("/category-distribution", response_model=list[CategoryDistribution])
def get_category_distribution(db: Session = Depends(get_db)) -> list[CategoryDistribution]:
    return dashboard_service.get_category_distribution(db)


@router.get("/top-customers", response_model=list[TopCustomer])
def get_top_customers(
    limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)
) -> list[TopCustomer]:
    return dashboard_service.get_top_customers(db, limit=limit)


@router.get("/top-products", response_model=list[TopProduct])
def get_top_products(
    limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)
) -> list[TopProduct]:
    return dashboard_service.get_top_products(db, limit=limit)


@router.get("/recent-orders", response_model=list[RecentOrder])
def get_recent_orders(
    limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)
) -> list[RecentOrder]:
    return dashboard_service.get_recent_orders(db, limit=limit)
