"""Evaluation metrics for the classification and regression models.

Pure functions only (arrays in, metrics dict out) — reusable from `train.py`
right after fitting, or standalone to re-evaluate a saved model against a
fresh test set later.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    root_mean_squared_error,
)

from utils.logging_utils import get_logger

logger = get_logger(__name__)


def evaluate_classifier(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray) -> dict:
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        # ROC-AUC is undefined with only one class present in y_true (can
        # happen on a tiny test split) — report None rather than crashing.
        "roc_auc": float(roc_auc_score(y_true, y_proba)) if len(set(y_true)) > 1 else None,
        "n_samples": int(len(y_true)),
    }
    logger.info("Classification metrics: %s", {k: v for k, v in metrics.items() if k != "n_samples"})
    return metrics


def evaluate_regressor(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    metrics = {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
        # R² is degenerate (undefined/misleading) with < 2 samples.
        "r2_score": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else None,
        "n_samples": int(len(y_true)),
    }
    logger.info("Regression metrics: %s", {k: v for k, v in metrics.items() if k != "n_samples"})
    return metrics
