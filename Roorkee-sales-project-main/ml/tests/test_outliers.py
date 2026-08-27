import pandas as pd

from preprocessing.outliers import OutlierCapper


def test_outlier_capper_clips_values_outside_iqr_fences(tmp_path):
    df = pd.DataFrame({"amount": [10, 11, 12, 13, 14, 15, 1000]})
    capper = OutlierCapper(columns=["amount"], multiplier=1.5).fit(df)
    transformed = capper.transform(df)

    lower, upper = capper.bounds_["amount"]
    assert transformed["amount"].max() == upper
    assert transformed["amount"].max() < 1000


def test_outlier_capper_save_and_load_roundtrip(tmp_path):
    df = pd.DataFrame({"amount": [10, 20, 30, 40, 1000]})
    capper = OutlierCapper(columns=["amount"]).fit(df)
    path = tmp_path / "bounds.json"
    capper.save(path)

    loaded = OutlierCapper.load(path)
    assert loaded.bounds_ == capper.bounds_

    # Loaded capper must apply the SAME (already-fitted) bounds without refitting.
    new_df = pd.DataFrame({"amount": [5000]})
    result = loaded.transform(new_df)
    assert result["amount"].iloc[0] == capper.bounds_["amount"][1]
