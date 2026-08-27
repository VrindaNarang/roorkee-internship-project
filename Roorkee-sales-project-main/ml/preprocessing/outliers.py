"""Outlier detection/capping using Tukey's IQR fences.

Implemented as a fit/transform class (not a stateless function) because
outlier bounds must be learned once from training data and then applied
*unchanged* at inference time — recomputing bounds on a single incoming
inference row would be meaningless, and recomputing them on live data would
let the definition of "outlier" silently drift over time.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from utils.logging_utils import get_logger

logger = get_logger(__name__)


class OutlierCapper:
    """Fits per-column [lower, upper] Tukey fences and clips values to them."""

    def __init__(self, columns: list[str], multiplier: float = 1.5) -> None:
        self.columns = columns
        self.multiplier = multiplier
        self.bounds_: dict[str, tuple[float, float]] = {}

    def fit(self, df: pd.DataFrame) -> "OutlierCapper":
        for col in self.columns:
            if col not in df.columns:
                continue
            q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - self.multiplier * iqr
            upper = q3 + self.multiplier * iqr
            self.bounds_[col] = (float(lower), float(upper))
        return self

    def transform(self, df: pd.DataFrame, *, table_name: str = "") -> pd.DataFrame:
        df = df.copy()
        for col, (lower, upper) in self.bounds_.items():
            if col not in df.columns:
                continue
            n_outliers = ((df[col] < lower) | (df[col] > upper)).sum()
            if n_outliers:
                logger.info(
                    "[%s] capped %d outlier(s) in '%s' to [%.2f, %.2f]",
                    table_name,
                    n_outliers,
                    col,
                    lower,
                    upper,
                )
            df[col] = df[col].clip(lower=lower, upper=upper)
        return df

    def fit_transform(self, df: pd.DataFrame, *, table_name: str = "") -> pd.DataFrame:
        return self.fit(df).transform(df, table_name=table_name)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"multiplier": self.multiplier, "bounds": self.bounds_}
        path.write_text(json.dumps(payload, indent=2))

    @classmethod
    def load(cls, path: Path) -> "OutlierCapper":
        payload = json.loads(path.read_text())
        instance = cls(columns=list(payload["bounds"].keys()), multiplier=payload["multiplier"])
        instance.bounds_ = {k: tuple(v) for k, v in payload["bounds"].items()}
        return instance
