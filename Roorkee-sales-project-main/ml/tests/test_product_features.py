import pandas as pd

from feature_engineering.product_features import build_product_features


def test_product_features_popularity_and_contribution():
    order_items = pd.DataFrame(
        {
            "product_id": [1, 1, 2],
            "quantity": [10, 5, 1],
            "line_total": [1000.0, 500.0, 100.0],
        }
    )
    products = pd.DataFrame(
        {
            "id": [1, 2],
            "sku": ["A-1", "B-1"],
            "name": ["Product A", "Product B"],
            "category_id": [100, 100],
            "unit_price": [100.0, 100.0],
            "is_active": [True, True],
        }
    )
    categories = pd.DataFrame({"id": [100], "name": ["Glassware"]})

    features = build_product_features(order_items, products, categories)

    product_a = features.loc[features["product_id"] == 1].iloc[0]
    product_b = features.loc[features["product_id"] == 2].iloc[0]

    assert product_a["units_sold"] == 15
    assert product_a["product_popularity_score"] == 1.0  # max units sold -> 1.0
    assert product_b["product_popularity_score"] == 1 / 15

    total_revenue = 1500.0 + 100.0
    assert round(product_a["revenue_contribution_pct"], 2) == round(1500 / total_revenue * 100, 2)
    # both products share the same category -> same category_revenue
    assert product_a["category_revenue"] == product_b["category_revenue"] == total_revenue
