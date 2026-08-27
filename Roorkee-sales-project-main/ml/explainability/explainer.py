"""Cached SHAP explainer construction.

Fitting a `shap.TreeExplainer` re-parses the whole booster (every tree, every
split) — cheap for one call, wasteful if repeated for every customer in a
batch or across repeated API-style calls within one process. This module
caches one explainer per model instance so it's built exactly once per
scoring run, no matter how many rows/plots are computed against it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap

from utils.logging_utils import get_logger

logger = get_logger(__name__)


class ExplainerCache:
    """Keyed by `id(model)` — correct as long as callers reuse the same
    loaded model object for a given scoring run (which `predict.py` and
    `train.py` both do), and safe by construction if they don't (a cache
    miss just costs one extra fit, never a wrong explainer).
    """

    def __init__(self) -> None:
        self._cache: dict[int, shap.TreeExplainer] = {}

    def get(self, model) -> shap.TreeExplainer:
        key = id(model)
        if key not in self._cache:
            logger.info("Fitting new SHAP TreeExplainer for model %s (cache miss)", type(model).__name__)
            self._cache[key] = shap.TreeExplainer(model)
        return self._cache[key]

    def clear(self) -> None:
        self._cache.clear()


# Process-wide singleton — `predict.py` scores potentially two models
# (classifier + regressor) across ~dozens of rows and several plot calls per
# run; every one of those should share this same cache.
_cache = ExplainerCache()


def get_explainer(model) -> shap.TreeExplainer:
    return _cache.get(model)


def raw_shap_matrix(model, X_encoded: pd.DataFrame) -> np.ndarray:
    """SHAP values for every row, shape-normalized.

    Normalizes across classifier/regressor and SHAP-library-version
    differences: sometimes a single (n, features) array, sometimes a list of
    one array per class (binary classifiers) — take the positive class's
    contributions in the latter case.
    """
    explainer = get_explainer(model)
    values = explainer.shap_values(X_encoded)
    if isinstance(values, list):
        values = values[1] if len(values) > 1 else values[0]
    values = np.asarray(values)
    if values.ndim == 3:
        # (n_samples, n_features, n_classes) shape some SHAP versions use for binary output.
        values = values[:, :, -1]
    return values
