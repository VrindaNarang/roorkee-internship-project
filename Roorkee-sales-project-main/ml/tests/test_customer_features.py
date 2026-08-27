import pandas as pd

from feature_engineering.customer_features import build_customer_features
from feature_engineering.time_features import add_time_features


def _colleges():
    return pd.DataFrame(
        {
            "id": [1, 2],
            "name": ["College A", "College B"],
            "institution_type": ["government", "private"],
            "region": ["North", "South"],
            "state": ["Delhi", "Karnataka"],
            "status": ["active", "active"],
            "onboarded_date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        }
    )


def _orders():
    # College 1 has two orders, one paid late; College 2 has none.
    return pd.DataFrame(
        {
            "id": [101, 102],
            "college_id": [1, 1],
            "order_date": pd.to_datetime(["2026-01-01", "2026-02-01"]),
            "total_amount": [1000.0, 2000.0],
            "payment_due_date": pd.to_datetime(["2026-01-15", "2026-02-15"]),
            "payment_received_date": pd.to_datetime(["2026-01-20", pd.NaT]),
        }
    )


def _order_items():
    return pd.DataFrame(
        {
            "id": [1, 2],
            "order_id": [101, 102],
            "product_id": [10, 10],
            "quantity": [5, 3],
            "line_total": [1000.0, 2000.0],
        }
    )


def _products():
    return pd.DataFrame({"id": [10], "category_id": [100]})


def _categories():
    return pd.DataFrame({"id": [100], "name": ["Glassware"]})


def test_build_customer_features_row_per_college_with_zero_fill():
    orders_time = add_time_features(_orders())
    reference_date = pd.Timestamp("2026-03-01")

    features = build_customer_features(
        _colleges(), orders_time, _order_items(), _products(), _categories(), reference_date
    )

    assert len(features) == 2  # every college gets a row, even with zero orders

    college_1 = features.loc[features["college_id"] == 1].iloc[0]
    assert college_1["total_orders"] == 2
    assert college_1["customer_lifetime_value"] == 3000.0
    assert college_1["average_order_value"] == 1500.0
    assert college_1["preferred_product_category"] == "Glassware"
    # last order 2026-02-01, reference 2026-03-01 -> 28 days
    assert college_1["days_since_last_purchase"] == 28

    college_2 = features.loc[features["college_id"] == 2].iloc[0]
    assert college_2["total_orders"] == 0
    assert college_2["customer_lifetime_value"] == 0
    assert college_2["preferred_product_category"] == "None"
    # never purchased -> recency falls back to full tenure
    assert college_2["days_since_last_purchase"] == college_2["tenure_days"]


def test_average_payment_delay_reflects_late_and_ontime_payments():
    orders_time = add_time_features(_orders())
    reference_date = pd.Timestamp("2026-03-01")

    features = build_customer_features(
        _colleges(), orders_time, _order_items(), _products(), _categories(), reference_date
    )
    college_1 = features.loc[features["college_id"] == 1].iloc[0]
    # order 101: paid 2026-01-20 vs due 2026-01-15 -> 5 days late
    # order 102: unpaid, due 2026-02-15, reference 2026-03-01 -> 14 days late so far
    assert college_1["average_payment_delay"] == (5 + 14) / 2
