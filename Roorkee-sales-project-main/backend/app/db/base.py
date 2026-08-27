from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models (see PROJECT_SPEC.md section 4).

    No models are defined yet in this milestone — this exists so the DB engine,
    Alembic, and future models all share one metadata object.
    """
