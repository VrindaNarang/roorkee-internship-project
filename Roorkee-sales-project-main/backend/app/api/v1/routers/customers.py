import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.core import cache
from app.db.session import get_db
from app.health_score.health_service import HealthScoreService
from app.schemas.customers import CustomerDetail, CustomerListResponse, CustomerOrderItem
from app.schemas.health_score import CustomerHealthDetail, CustomerHealthListItem, RecalculateResponse
from app.services import customers_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=CustomerListResponse)
def list_customers(
    search: str | None = None,
    state: str | None = None,
    institution_type: str | None = Query(None, pattern="^(government|private)$"),
    status: str | None = Query(None, pattern="^(active|dormant)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CustomerListResponse:
    return customers_service.list_customers(
        db,
        search=search,
        state=state,
        institution_type=institution_type,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/states", response_model=list[str])
def list_states(db: Session = Depends(get_db)) -> list[str]:
    return customers_service.get_distinct_states(db)


# --- Health scoring routes registered before /{customer_id} so literal paths
# like "/health" and "/critical" aren't swallowed by the dynamic segment. ---


@router.get("/health", response_model=list[CustomerHealthListItem])
def list_customer_health(db: Session = Depends(get_db)) -> list[CustomerHealthListItem]:
    """Latest health score (+ trend) for every customer."""
    items = HealthScoreService(db).list_latest()
    items.sort(key=lambda i: i["health_score"], reverse=True)
    return items


@router.post(
    "/health",
    response_model=RecalculateResponse,
    dependencies=[Depends(require_role("admin", "sales_manager"))],
)
def recalculate_customer_health(db: Session = Depends(get_db)) -> RecalculateResponse:
    """Runs a full health-score recalculation for every customer.

    This is the hook point for "recalculate whenever new sales data is
    imported" — call this at the end of a successful data-import job once
    that exists. Until then it's triggered manually / on a schedule.

    Restricted to admin/sales_manager (not sales_executive) — this rewrites
    every customer's health score across the whole business, not a
    read-only lookup.
    """
    summary = HealthScoreService(db).recalculate()
    cache.clear_all()  # new scores must be visible immediately, not after the read-cache TTL
    return RecalculateResponse(
        scored_at=summary.scored_at,
        total_customers=summary.total_customers,
        healthy=summary.healthy,
        at_risk=summary.at_risk,
        critical=summary.critical,
        model_version=summary.model_version,
    )


@router.get("/critical", response_model=list[CustomerHealthListItem])
def list_critical_customers(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
) -> list[CustomerHealthListItem]:
    """Customers in the critical band (score 0-49), worst first."""
    items = HealthScoreService(db).list_latest(status="critical")
    items.sort(key=lambda i: i["health_score"])
    return items[:limit]


@router.get("/healthy", response_model=list[CustomerHealthListItem])
def list_healthy_customers(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
) -> list[CustomerHealthListItem]:
    """Customers in the healthy band (score 80-100), best first."""
    items = HealthScoreService(db).list_latest(status="healthy")
    items.sort(key=lambda i: i["health_score"], reverse=True)
    return items[:limit]


@router.get("/at-risk", response_model=list[CustomerHealthListItem])
def list_at_risk_customers(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
) -> list[CustomerHealthListItem]:
    """Customers in the at-risk band (score 50-79), worst first."""
    items = HealthScoreService(db).list_latest(status="at_risk")
    items.sort(key=lambda i: i["health_score"])
    return items[:limit]


@router.get("/{customer_id}", response_model=CustomerDetail)
def get_customer(customer_id: int, db: Session = Depends(get_db)) -> CustomerDetail:
    customer = customers_service.get_customer_detail(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/{customer_id}/orders", response_model=list[CustomerOrderItem])
def get_customer_orders(customer_id: int, db: Session = Depends(get_db)) -> list[CustomerOrderItem]:
    customer = customers_service.get_customer_detail(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customers_service.get_customer_orders(db, customer_id)


@router.get("/{customer_id}/health", response_model=CustomerHealthDetail)
def get_customer_health(customer_id: int, db: Session = Depends(get_db)) -> CustomerHealthDetail:
    customer = customers_service.get_customer_detail(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    health = HealthScoreService(db).get_for_customer(customer_id)
    if health is None:
        raise HTTPException(
            status_code=404, detail="No health score computed yet for this customer — POST /customers/health first"
        )
    return health
