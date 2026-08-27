"""Generic + per-table data cleaning.

Split into two layers on purpose:
  - generic helpers (`drop_duplicate_records`, `handle_missing_values`,
    `validate_dtypes`, `parse_dates`) that know nothing about the sales
    domain and are reusable across any table,
  - per-table `clean_*` functions that apply those helpers with the specific
    rules each table needs.

Every function is a pure `DataFrame -> DataFrame` transform (no hidden
state), so the exact same code path runs at training time and at inference
time — the whole point of a reusable preprocessing pipeline.
"""

from __future__ import annotations

import pandas as pd

from utils.logging_utils import get_logger

logger = get_logger(__name__)


# --------------------------------------------------------------------------
# Generic, reusable helpers
# --------------------------------------------------------------------------


def drop_duplicate_records(df: pd.DataFrame, subset: list[str], *, table_name: str = "") -> pd.DataFrame:
    before = len(df)
    deduped = df.drop_duplicates(subset=subset, keep="last")
    dropped = before - len(deduped)
    if dropped:
        logger.info("[%s] dropped %d duplicate record(s) on %s", table_name, dropped, subset)
    return deduped.reset_index(drop=True)


def handle_missing_values(
    df: pd.DataFrame,
    *,
    drop_if_missing: list[str] | None = None,
    fill_values: dict[str, object] | None = None,
    fill_median: list[str] | None = None,
    table_name: str = "",
) -> pd.DataFrame:
    """Applies an explicit missing-value strategy column by column.

    - `drop_if_missing`: rows with a null in any of these columns are removed
      (used for fields a row is meaningless without, e.g. a financial total).
    - `fill_values`: literal fill value per column (e.g. `{"contact_phone": "unknown"}`).
    - `fill_median`: numeric columns imputed with their own median.
    """
    df = df.copy()

    for col in fill_median or []:
        if col not in df.columns:
            continue
        n_missing = df[col].isna().sum()
        if n_missing:
            median = df[col].median()
            df[col] = df[col].fillna(median)
            logger.info("[%s] filled %d missing '%s' with median=%.2f", table_name, n_missing, col, median)

    for col, value in (fill_values or {}).items():
        if col not in df.columns:
            continue
        n_missing = df[col].isna().sum()
        if n_missing:
            df[col] = df[col].fillna(value)
            logger.info("[%s] filled %d missing '%s' with '%s'", table_name, n_missing, col, value)

    if drop_if_missing:
        before = len(df)
        df = df.dropna(subset=[c for c in drop_if_missing if c in df.columns])
        dropped = before - len(df)
        if dropped:
            logger.warning(
                "[%s] dropped %d row(s) with missing required field(s) %s",
                table_name,
                dropped,
                drop_if_missing,
            )

    return df.reset_index(drop=True)


def validate_dtypes(df: pd.DataFrame, dtype_map: dict[str, str], *, table_name: str = "") -> pd.DataFrame:
    """Coerces columns to the expected dtype, turning unparseable values into NaN
    instead of raising — bad source data becomes a visible missing value, not a
    crash, which is the right failure mode for a pipeline that also has to run
    unattended at inference time.
    """
    df = df.copy()
    for col, dtype in dtype_map.items():
        if col not in df.columns:
            continue
        original = df[col]
        if dtype in ("float64", "float", "int64", "int"):
            coerced = pd.to_numeric(original, errors="coerce")
        else:
            coerced = original.astype(dtype, errors="ignore")
        n_bad = coerced.isna().sum() - original.isna().sum()
        if n_bad and n_bad > 0:
            logger.warning("[%s] column '%s': %d value(s) failed dtype coercion to %s", table_name, col, n_bad, dtype)
        df[col] = coerced
    return df


def parse_dates(df: pd.DataFrame, date_cols: list[str], *, table_name: str = "") -> pd.DataFrame:
    df = df.copy()
    for col in date_cols:
        if col not in df.columns:
            continue
        original_non_null = df[col].notna().sum()
        df[col] = pd.to_datetime(df[col], errors="coerce")
        new_non_null = df[col].notna().sum()
        invalid = original_non_null - new_non_null
        if invalid > 0:
            logger.warning("[%s] column '%s': %d unparseable date(s) coerced to NaT", table_name, col, invalid)
    return df


# --------------------------------------------------------------------------
# Per-table cleaning
# --------------------------------------------------------------------------


def clean_colleges(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_duplicate_records(df, subset=["id"], table_name="colleges")
    df = validate_dtypes(df, {"id": "int64"}, table_name="colleges")
    df = parse_dates(df, ["onboarded_date", "created_at", "updated_at"], table_name="colleges")
    df = handle_missing_values(
        df,
        drop_if_missing=["id", "name", "institution_type", "region", "state"],
        fill_values={"contact_phone": "unknown", "contact_email": "unknown"},
        table_name="colleges",
    )
    return df


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_duplicate_records(df, subset=["id"], table_name="products")
    df = validate_dtypes(
        df, {"id": "int64", "category_id": "int64", "unit_price": "float64", "cost_price": "float64"},
        table_name="products",
    )
    df = handle_missing_values(
        df,
        drop_if_missing=["id", "name", "category_id"],
        fill_median=["unit_price", "cost_price"],
        table_name="products",
    )
    return df


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_duplicate_records(df, subset=["id"], table_name="orders")
    df = validate_dtypes(
        df,
        {
            "id": "int64",
            "college_id": "int64",
            "subtotal": "float64",
            "tax_amount": "float64",
            "total_amount": "float64",
            "discount_pct": "float64",
        },
        table_name="orders",
    )
    df = parse_dates(df, ["order_date", "payment_due_date", "payment_received_date"], table_name="orders")

    # An order can't be paid before it was placed — a data-entry/import error,
    # not a value worth keeping. Null it out rather than dropping the whole row.
    invalid_payment = df["payment_received_date"].notna() & (df["payment_received_date"] < df["order_date"])
    if invalid_payment.any():
        logger.warning(
            "[orders] %d row(s) had payment_received_date before order_date — nulled out",
            int(invalid_payment.sum()),
        )
        df.loc[invalid_payment, "payment_received_date"] = pd.NaT

    df = handle_missing_values(
        df,
        drop_if_missing=["id", "college_id", "order_date", "total_amount"],
        table_name="orders",
    )
    return df


def clean_order_items(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_duplicate_records(df, subset=["id"], table_name="order_items")
    df = validate_dtypes(
        df,
        {
            "id": "int64",
            "order_id": "int64",
            "product_id": "int64",
            "quantity": "int64",
            "unit_price": "float64",
            "line_total": "float64",
        },
        table_name="order_items",
    )
    df = handle_missing_values(
        df,
        drop_if_missing=["id", "order_id", "product_id", "quantity", "line_total"],
        table_name="order_items",
    )
    # A non-positive quantity is not a valid line item.
    before = len(df)
    df = df[df["quantity"] > 0].reset_index(drop=True)
    if before - len(df):
        logger.warning("[order_items] dropped %d row(s) with non-positive quantity", before - len(df))
    return df


def clean_all(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "colleges": clean_colleges(raw["colleges"]),
        "product_categories": drop_duplicate_records(
            raw["product_categories"], subset=["id"], table_name="product_categories"
        ),
        "products": clean_products(raw["products"]),
        "sales_reps": drop_duplicate_records(raw["sales_reps"], subset=["id"], table_name="sales_reps"),
        "orders": clean_orders(raw["orders"]),
        "order_items": clean_order_items(raw["order_items"]),
    }
