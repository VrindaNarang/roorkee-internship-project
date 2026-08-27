"""Generates and saves the five SHAP visualization types this milestone
requires, all working against *aggregated original features* (not one-hot
dummy columns) — a sales manager looking at a plot should see "state", not
"state_Maharashtra".

Headless by construction (`matplotlib.use("Agg")` before pyplot is ever
imported) since this runs in a batch job with no display.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import shap

from explainability.config import (
    BAR_FIGSIZE,
    DEPENDENCE_FIGSIZE,
    FORCE_FIGSIZE,
    PLOT_DPI,
    SUMMARY_FIGSIZE,
    WATERFALL_FIGSIZE,
)
from utils.logging_utils import get_logger

logger = get_logger(__name__)


def _save_and_close(fig, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=PLOT_DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved plot -> %s", path)
    return str(path)


def waterfall_plot(
    aggregated_shap_row: np.ndarray, base_value: float, raw_values: list, feature_names: list[str], save_path: Path
) -> str:
    """One customer's prediction, decomposed feature by feature from the
    model's average output up to their specific predicted value.
    """
    explanation = shap.Explanation(
        values=aggregated_shap_row,
        base_values=base_value,
        data=np.array(raw_values, dtype=object),
        feature_names=feature_names,
    )
    fig = plt.figure(figsize=WATERFALL_FIGSIZE)
    shap.plots.waterfall(explanation, show=False)
    return _save_and_close(fig, save_path)


def force_plot(
    aggregated_shap_row: np.ndarray, base_value: float, raw_values: list, feature_names: list[str], save_path: Path
) -> str:
    """Same information as the waterfall, compressed into a single
    push-pull bar — a compact alternative some readers find quicker to scan.
    """
    fig = plt.figure(figsize=FORCE_FIGSIZE)
    shap.force_plot(
        base_value,
        aggregated_shap_row,
        list(raw_values),
        feature_names=feature_names,
        matplotlib=True,
        show=False,
    )
    return _save_and_close(plt.gcf(), save_path)


def summary_plot(aggregated_matrix: np.ndarray, raw_matrix: np.ndarray, feature_names: list[str], save_path: Path) -> str:
    """The classic SHAP beeswarm: every customer, every feature, colored by
    that customer's raw feature value — shows both *how much* and *in which
    direction* each feature matters, across the whole customer base at once.
    """
    fig = plt.figure(figsize=SUMMARY_FIGSIZE)
    shap.summary_plot(aggregated_matrix, features=raw_matrix, feature_names=feature_names, show=False)
    return _save_and_close(plt.gcf(), save_path)


def bar_plot(aggregated_matrix: np.ndarray, feature_names: list[str], save_path: Path) -> str:
    """Mean absolute contribution per feature — the simplest possible
    "what matters most overall" chart.
    """
    fig = plt.figure(figsize=BAR_FIGSIZE)
    shap.summary_plot(aggregated_matrix, feature_names=feature_names, plot_type="bar", show=False)
    return _save_and_close(plt.gcf(), save_path)


def dependence_plot(
    feature: str, aggregated_matrix: np.ndarray, raw_matrix: np.ndarray, feature_names: list[str], save_path: Path
) -> str:
    """How a single feature's *raw value* relates to its SHAP contribution
    across every customer — e.g. does payment delay hurt more once it passes
    some threshold, or is the relationship linear?
    """
    fig = plt.figure(figsize=DEPENDENCE_FIGSIZE)
    shap.dependence_plot(
        feature,
        aggregated_matrix,
        raw_matrix,
        feature_names=feature_names,
        interaction_index=None,
        show=False,
    )
    return _save_and_close(plt.gcf(), save_path)
