import numpy as np

from explainability.utils import aggregate_matrix, aggregate_row, build_reason_sentences, top_contributors


def test_aggregate_row_sums_one_hot_dummies_back_to_original_feature():
    encoded_columns = ["state_Maharashtra", "state_Gujarat", "days_since_last_purchase_scaled"]
    shap_row = np.array([0.2, -0.05, -0.4])

    aggregated = aggregate_row(
        shap_row, encoded_columns, categorical_cols=["state"], numeric_cols=["days_since_last_purchase"]
    )

    assert aggregated["state"] == 0.2 + (-0.05)
    assert aggregated["days_since_last_purchase"] == -0.4


def test_top_contributors_ranks_by_absolute_value_and_labels_direction():
    aggregated = {"a": 0.1, "b": -0.9, "c": 0.5}
    result = top_contributors(aggregated, top_n=2)

    assert [r["feature"] for r in result] == ["b", "c"]
    assert result[0]["direction"] == "decreases"
    assert result[1]["direction"] == "increases"


def test_top_contributors_respects_top_n():
    aggregated = {f"f{i}": float(i) for i in range(10)}
    result = top_contributors(aggregated, top_n=3)
    assert len(result) == 3


def test_aggregate_matrix_produces_stable_feature_order_across_rows():
    encoded_columns = ["days_since_last_purchase_scaled", "state_Maharashtra", "state_Gujarat"]
    matrix = np.array(
        [
            [-0.4, 0.2, -0.05],
            [0.1, 0.0, 0.3],
        ]
    )
    aggregated, feature_names = aggregate_matrix(
        matrix, encoded_columns, categorical_cols=["state"], numeric_cols=["days_since_last_purchase"]
    )

    assert feature_names == ["days_since_last_purchase", "state"]
    assert aggregated[0].tolist() == [-0.4, 0.2 + (-0.05)]
    assert aggregated[1].tolist() == [0.1, 0.0 + 0.3]


def test_build_reason_sentences_uses_raw_values_and_direction_prefix():
    contributors = [
        {"feature": "average_payment_delay", "value": -0.11, "direction": "decreases"},
        {"feature": "customer_lifetime_value", "value": 0.15, "direction": "increases"},
    ]
    raw_values = {"average_payment_delay": 18, "customer_lifetime_value": 5_000_000}

    sentences = build_reason_sentences(contributors, raw_values)

    assert sentences[0] == "- Payment delayed by 18 days"
    assert sentences[1] == "+ High customer lifetime value"


def test_build_reason_sentences_falls_back_for_unknown_feature():
    contributors = [{"feature": "some_new_feature", "value": 0.2, "direction": "increases"}]
    sentences = build_reason_sentences(contributors, raw_values={})
    assert sentences == ["+ Some new feature (increases likelihood)"]
