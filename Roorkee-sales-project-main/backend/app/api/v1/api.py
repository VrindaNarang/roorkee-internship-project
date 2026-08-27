from fastapi import APIRouter, Depends

from app.api.v1.routers import (
    analytics,
    auth,
    copilot,
    customers,
    dashboard,
    explain,
    ml_admin,
    predictions,
    products,
    recommendations,
)
from app.auth.dependencies import get_current_user

api_router = APIRouter()

# `/auth/login` must stay unprotected (a request without a token yet needs to
# be able to reach it); every other router is mounted on `_protected_router`
# below, which applies `get_current_user` once for all of them instead of
# sprinkling `Depends(get_current_user)` across every route function.
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

_protected_router = APIRouter(dependencies=[Depends(get_current_user)])

_protected_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
_protected_router.include_router(customers.router, prefix="/customers", tags=["customers"])
_protected_router.include_router(products.router, prefix="/products", tags=["products"])
_protected_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
_protected_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
_protected_router.include_router(explain.router, prefix="/explain", tags=["explainability"])
_protected_router.include_router(
    recommendations.router, prefix="/recommendations", tags=["recommendations"]
)
_protected_router.include_router(ml_admin.router, prefix="/ml", tags=["ml"])
_protected_router.include_router(copilot.router, prefix="/copilot", tags=["copilot"])

api_router.include_router(_protected_router)
