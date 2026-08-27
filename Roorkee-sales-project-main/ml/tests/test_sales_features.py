import pandas as pd

from feature_engineering.sales_features import build_sales_features
from feature_engineering.time_features import add_time_features


def test_order_consistency_higher_for_regular_cadence():
    regular = pd.DataFrame(
        {
            "college_id": [1, 1, 1, 1],
            "order_date": pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-03", "2026-04-01"]),
            "total_amount": [100.0, 100.0, 100.0, 100.0],
        }
    )
    bursty = pd.DataFrame(
        {
            "college_id": [2, 2, 2, 2],
            "order_date": pd.to_datetime(["2026-01-01", "2026-01-03", "2026-01-05", "2026-04-01"]),
            "total_amount": [100.0, 100.0, 100.0, 100.0],
        }
    )
    orders_time = add_time_features(pd.concat([regular, bursty], ignore_index=True))
    reference_date = pd.Timestamp("2026-05-01")

    features = build_sales_features(orders_time, reference_date)
    regular_score = features.loc[features["college_id"] == 1, "order_consistency"].iloc[0]
    bursty_score = features.loc[features["college_id"] == 2, "order_consistency"].iloc[0]

    assert regular_score > bursty_score


def test_seasonal_purchase_pattern_picks_highest_revenue_quarter():
    orders = pd.DataFrame(
        {
            "college_id": [1, 1],
            "order_date": pd.to_datetime(["2026-01-15", "2026-07-15"]),  # Q1 vs Q3
            "total_amount": [100.0, 900.0],
        }
    )
    orders_time = add_time_features(orders)
    features = build_sales_features(orders_time, pd.Timestamp("2026-08-01"))
    assert features.loc[features["college_id"] == 1, "seasonal_purchase_pattern"].iloc[0] == "Q3"
