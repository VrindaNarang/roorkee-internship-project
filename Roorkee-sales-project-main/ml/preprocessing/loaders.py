"""Loads raw tables from PostgreSQL into pandas DataFrames.

Kept deliberately dumb (no cleaning/joining here) so `preprocessing.cleaning`
and `feature_engineering.*` each have a single, well-defined job. This module
is the only place that talks to the database.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, create_engine

from config.settings import Settings, get_settings
from utils.logging_utils import get_logger

logger = get_logger(__name__)

TABLES = ("colleges", "product_categories", "products", "sales_reps", "orders", "order_items")


def get_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


def load_raw_tables(engine: Engine | None = None) -> dict[str, pd.DataFrame]:
    """Loads every table the pipeline needs into memory as-is.

    Returns a dict keyed by table name so callers can destructure explicitly
    (`raw["orders"]`) rather than relying on positional order.
    """
    engine = engine or get_engine()
    raw: dict[str, pd.DataFrame] = {}
    for table in TABLES:
        df = pd.read_sql_table(table, engine)
        # SQLAlchemy reflection returns column labels as `quoted_name` (a str
        # subclass) rather than plain `str`. `.astype(str)` is a no-op here
        # since quoted_name already *is* a str subclass — rebuild the Index
        # with genuine `str` objects instead. Harmless almost everywhere, but
        # scikit-learn's strict column-name-type check rejects it later in
        # the pipeline — normalize once, here, at the source.
        df.columns = pd.Index([str(c) for c in df.columns])
        logger.info("Loaded table '%s': %d rows, %d columns", table, len(df), df.shape[1])
        raw[table] = df
    return raw
