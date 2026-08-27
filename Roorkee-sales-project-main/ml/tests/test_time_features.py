import pandas as pd

from config.settings import get_settings
from feature_engineering.time_features import add_time_features


def _orders():
    return pd.DataFrame(
        {
            "college_id": [1, 1, 1, 2],
            "order_date": pd.to_datetime(
                ["2025-06-10", "2025-07-15", "2025-09-01", "2026-02-01"]
            ),
        }
    )


def test_financial_year_label_follows_april_start():
    df = add_time_features(_orders())
    # 2025-06-10 -> FY2025-26 (before Apr the label would roll back a year)
    assert df.loc[df["order_date"] == "2025-06-10", "financial_year"].iloc[0] == "FY2025-26"
    # 2026-02-01 falls before April, so it belongs to FY2025-26 too
    assert df.loc[df["order_date"] == "2026-02-01", "financial_year"].iloc[0] == "FY2025-26"


def test_admission_season_indicator_flags_june_to_august():
    settings = get_settings()
    df = add_time_features(_orders(), settings)
    june_row = df.loc[df["order_date"] == "2025-06-10"].iloc[0]
    september_row = df.loc[df["order_date"] == "2025-09-01"].iloc[0]
    assert june_row["admission_season_indicator"] == 1
    assert september_row["admission_season_indicator"] == 0


def test_days_since_prev_order_computed_per_college():
    df = add_time_features(_orders())
    college_1 = df[df["college_id"] == 1].sort_values("order_date")
    # first order for a college has no previous order
    assert pd.isna(college_1["days_since_prev_order"].iloc[0])
    # 2025-06-10 -> 2025-07-15 is 35 days
    assert college_1["days_since_prev_order"].iloc[1] == 35
    # college 2 has a single order, so also NaN
    college_2 = df[df["college_id"] == 2]
    assert pd.isna(college_2["days_since_prev_order"].iloc[0])
