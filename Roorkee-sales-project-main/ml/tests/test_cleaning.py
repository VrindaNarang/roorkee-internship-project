import numpy as np
import pandas as pd

from preprocessing.cleaning import (
    drop_duplicate_records,
    handle_missing_values,
    parse_dates,
    validate_dtypes,
)


def test_drop_duplicate_records_keeps_last_and_dedupes():
    df = pd.DataFrame({"id": [1, 1, 2], "value": ["old", "new", "x"]})
    result = drop_duplicate_records(df, subset=["id"])
    assert len(result) == 2
    assert result.loc[result["id"] == 1, "value"].iloc[0] == "new"


def test_handle_missing_values_drop_fill_median_and_literal():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["a", None, "c"],
            "price": [10.0, np.nan, 30.0],
            "phone": [None, "123", None],
        }
    )
    result = handle_missing_values(
        df,
        drop_if_missing=["name"],
        fill_median=["price"],
        fill_values={"phone": "unknown"},
    )
    # row 2 (name=None) dropped
    assert len(result) == 2
    assert result["price"].isna().sum() == 0


def test_validate_dtypes_coerces_bad_numeric_to_nan():
    df = pd.DataFrame({"amount": ["10.5", "not-a-number", "20"]})
    result = validate_dtypes(df, {"amount": "float64"})
    assert result["amount"].iloc[0] == 10.5
    assert pd.isna(result["amount"].iloc[1])
    assert result["amount"].iloc[2] == 20.0


def test_parse_dates_coerces_invalid_to_nat():
    df = pd.DataFrame({"order_date": ["2026-01-15", "not-a-date", "2026-02-01"]})
    result = parse_dates(df, ["order_date"])
    assert pd.api.types.is_datetime64_any_dtype(result["order_date"])
    assert result["order_date"].isna().sum() == 1
