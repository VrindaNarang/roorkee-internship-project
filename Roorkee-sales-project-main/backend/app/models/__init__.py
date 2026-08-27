# SQLAlchemy ORM models (see PROJECT_SPEC.md section 4).
# Imported here so Alembic's autogenerate and Base.metadata see every table.
from app.models.college import College
from app.models.health_score import CustomerHealthScore
from app.models.model_registry import ModelRegistry
from app.models.order import Order, OrderItem
from app.models.prediction import Prediction
from app.models.product import Product, ProductCategory
from app.models.sales_rep import SalesRep
from app.models.user import User

__all__ = [
    "College",
    "CustomerHealthScore",
    "ModelRegistry",
    "Order",
    "OrderItem",
    "Prediction",
    "Product",
    "ProductCategory",
    "SalesRep",
    "User",
]
