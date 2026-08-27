"""Categorical encoding + numeric scaling, as a fit/transform/save/load unit.

Reused as-is for both training and inference: `fit_transform` on the training
feature set, then `transform` (using the encoder/scaler already fitted, no
refitting) on whatever needs scoring later. `handle_unknown="ignore"` on the
one-hot encoder means a category never seen during fit (e.g. a brand-new
state) degrades gracefully to all-zero columns instead of crashing inference.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from utils.logging_utils import get_logger

logger = get_logger(__name__)


class FeatureEncoder:
    """One-hot encodes categorical columns and standard-scales numeric columns.

    Passthrough columns (ids, labels, human-readable reference fields) are
    left untouched and re-attached after the transform.
    """

    def __init__(self, categorical_cols: list[str], numeric_cols: list[str]) -> None:
        self.categorical_cols = categorical_cols
        self.numeric_cols = numeric_cols
        self.one_hot = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        self.scaler = StandardScaler()
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> "FeatureEncoder":
        if self.categorical_cols:
            self.one_hot.fit(df[self.categorical_cols].astype(str))
        if self.numeric_cols:
            self.scaler.fit(df[self.numeric_cols])
        self._fitted = True
        logger.info(
            "FeatureEncoder fitted: %d categorical col(s) -> %d one-hot col(s), %d numeric col(s) scaled",
            len(self.categorical_cols),
            len(self.one_hot.get_feature_names_out()) if self.categorical_cols else 0,
            len(self.numeric_cols),
        )
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("FeatureEncoder.transform() called before fit()")

        passthrough_cols = [c for c in df.columns if c not in self.categorical_cols + self.numeric_cols]
        result = df[passthrough_cols].reset_index(drop=True)

        if self.categorical_cols:
            encoded = self.one_hot.transform(df[self.categorical_cols].astype(str))
            encoded_df = pd.DataFrame(
                encoded, columns=self.one_hot.get_feature_names_out(self.categorical_cols)
            )
            result = pd.concat([result, encoded_df], axis=1)

        if self.numeric_cols:
            scaled = self.scaler.transform(df[self.numeric_cols])
            scaled_df = pd.DataFrame(scaled, columns=[f"{c}_scaled" for c in self.numeric_cols])
            result = pd.concat([result, scaled_df], axis=1)

        return result

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        logger.info("Saved FeatureEncoder to %s", path)

    @classmethod
    def load(cls, path: Path) -> "FeatureEncoder":
        return joblib.load(path)
