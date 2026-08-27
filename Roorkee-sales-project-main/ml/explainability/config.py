"""Configuration for the Explainable AI (SHAP) module.

Paths and tunable constants only — no logic here, so `explainer.py`,
`shap_service.py`, and `plot_generator.py` all read the same knobs.
"""

from __future__ import annotations

from prediction.config import ARTIFACTS_DIR

PLOTS_DIR = ARTIFACTS_DIR / "plots"

# How many top contributors to surface per prediction (local) vs across the
# whole customer base (global). Kept small on purpose — a sales manager
# wants the 5 factors that matter, not all 14.
TOP_N_LOCAL = 5
TOP_N_GLOBAL = 10

# Dependence plots are one-per-feature and relatively expensive to eyeball in
# bulk, so only the top K globally-important features get one.
DEPENDENCE_PLOT_TOP_K = 3

# Matplotlib figure sizing for the saved PNGs (inches).
WATERFALL_FIGSIZE = (8, 5)
FORCE_FIGSIZE = (10, 3)
SUMMARY_FIGSIZE = (8, 6)
BAR_FIGSIZE = (8, 5)
DEPENDENCE_FIGSIZE = (6, 5)
PLOT_DPI = 110
