import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.products import (
    ProductCategoryOut,
    ProductDetail,
    ProductListResponse,
    ProductSalesTrendPoint,
)
from app.services import products_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=ProductListResponse)
def list_products(
    search: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ProductListResponse:
    return products_service.list_products(
        db, search=search, category=category, is_active=is_active, page=page, page_size=page_size
    )


@router.get("/categories", response_model=list[ProductCategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[ProductCategoryOut]:
    return products_service.get_categories(db)


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductDetail:
    product = products_service.get_product_detail(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/{product_id}/sales-trend", response_model=list[ProductSalesTrendPoint])
def get_product_sales_trend(
    product_id: int, months: int = Query(12, ge=1, le=36), db: Session = Depends(get_db)
) -> list[ProductSalesTrendPoint]:
    product = products_service.get_product_detail(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return products_service.get_product_sales_trend(db, product_id, months=months)
