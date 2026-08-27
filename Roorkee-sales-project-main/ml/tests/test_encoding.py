import pandas as pd

from preprocessing.encoding import FeatureEncoder


def _df():
    return pd.DataFrame(
        {
            "college_id": [1, 2, 3],
            "region": ["North", "South", "North"],
            "revenue": [100.0, 200.0, 300.0],
        }
    )


def test_fit_transform_produces_one_hot_and_scaled_columns():
    encoder = FeatureEncoder(categorical_cols=["region"], numeric_cols=["revenue"])
    result = encoder.fit_transform(_df())

    assert "college_id" in result.columns  # passthrough untouched
    assert "region_North" in result.columns and "region_South" in result.columns
    assert "revenue_scaled" in result.columns
    # scaled column should be standardized (mean ~ 0)
    assert abs(result["revenue_scaled"].mean()) < 1e-9


def test_unseen_category_at_transform_time_does_not_raise():
    encoder = FeatureEncoder(categorical_cols=["region"], numeric_cols=["revenue"]).fit(_df())
    unseen = pd.DataFrame({"college_id": [4], "region": ["East"], "revenue": [150.0]})
    result = encoder.transform(unseen)
    # handle_unknown="ignore" -> all region_* columns are 0 for the unseen category
    assert result[["region_North", "region_South"]].iloc[0].sum() == 0


def test_save_and_load_roundtrip(tmp_path):
    encoder = FeatureEncoder(categorical_cols=["region"], numeric_cols=["revenue"]).fit(_df())
    path = tmp_path / "encoder.joblib"
    encoder.save(path)

    loaded = FeatureEncoder.load(path)
    pd.testing.assert_frame_equal(loaded.transform(_df()), encoder.transform(_df()))
