"""Batch scoring: runs the currently-active models over every college,
writes fresh predictions + SHAP explanations into Postgres, and generates
the explainability plots (global + per-customer) the dashboard reads.

Deliberately separate from `train.py` — this can be re-run on its own (e.g.
on a schedule) to refresh predictions against the latest order data without
retraining, exactly like PROJECT_SPEC.md section 6's "Scoring" step being
independent of "Training".

Run with:
    cd ml
    .venv/Scripts/python.exe -m prediction.predict
"""

from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

from explainability import plot_generator, shap_service
from explainability.config import DEPENDENCE_PLOT_TOP_K, PLOTS_DIR
from explainability.explainer import get_explainer
from explainability.utils import aggregate_matrix
from pipeline import MLPipeline, PipelineResult
from prediction import inference, model_loader
from prediction.config import (
    ALL_FEATURES,
    ARTIFACTS_DIR,
    CATEGORICAL_FEATURES,
    MODEL_NAME_CLASSIFIER,
    MODEL_NAME_REGRESSOR,
    NUMERIC_FEATURES,
)
from preprocessing.loaders import get_engine
from utils.logging_utils import get_logger

logger = get_logger(__name__)

GLOBAL_IMPORTANCE_PATH = ARTIFACTS_DIR / "global_feature_importance.json"


def _base_value(model) -> float:
    explainer = get_explainer(model)
    bv = explainer.expected_value
    if isinstance(bv, (list, np.ndarray)):
        bv = bv[-1] if len(bv) > 1 else bv[0]
    return float(bv)


def write_predictions(
    engine: Engine,
    predictions_df: pd.DataFrame,
    classifier_explanations: list[dict],
    regressor_explanations: list[dict],
    classifier_version: str,
    regressor_version: str,
) -> None:
    """Appends one `purchase_probability` row and one `expected_order_value`
    row per college — matching PROJECT_SPEC.md section 4.2's `predictions`
    table shape (one row per prediction_type rather than a wide table).
    Each row's `shap_explanation` carries contributors (split positive/
    negative) plus plain-English reason sentences.
    """
    rows = []
    for i, record in enumerate(predictions_df.itertuples(index=False)):
        rows.append(
            {
                "college_id": record.college_id,
                "prediction_type": "purchase_probability",
                "predicted_value": float(record.purchase_probability),
                "probability": float(record.purchase_probability),
                "model_version": classifier_version,
                "shap_explanation": json.dumps(classifier_explanations[i]),
            }
        )
        rows.append(
            {
                "college_id": record.college_id,
                "prediction_type": "expected_order_value",
                "predicted_value": float(record.expected_order_value),
                "probability": None,
                "model_version": regressor_version,
                "shap_explanation": json.dumps(regressor_explanations[i]),
            }
        )

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO predictions
                    (college_id, prediction_type, predicted_value, probability, prediction_date, model_version, shap_explanation)
                VALUES
                    (:college_id, :prediction_type, :predicted_value, :probability, now(), :model_version, CAST(:shap_explanation AS JSON))
                """
            ),
            rows,
        )
    logger.info("Wrote %d prediction rows (%d colleges x 2 types), each with a SHAP explanation", len(rows), len(predictions_df))


def write_global_importance(classifier_global: dict, regressor_global: dict, model_version: str) -> None:
    """Overwrites the single "current" global-importance summary file — it
    describes the latest scoring run, not a specific historical version, so
    it isn't kept alongside the versioned model artifacts.
    """
    GLOBAL_IMPORTANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model_version": model_version,
        "purchase_probability": classifier_global,
        "expected_order_value": regressor_global,
    }
    GLOBAL_IMPORTANCE_PATH.write_text(json.dumps(payload, indent=2))
    logger.info("Wrote global feature importance -> %s", GLOBAL_IMPORTANCE_PATH)


def generate_plots(
    models: model_loader.LoadedModels,
    model_input: pd.DataFrame,
    raw_feature_rows: list[dict],
    college_ids: list[int],
    classifier_global: dict,
) -> None:
    """Generates every plot type this milestone requires: global (summary,
    bar, dependence) for both models, plus per-customer (waterfall, force)
    for the purchase-probability classifier — the "will they buy" question
    a sales manager is most likely to want to see decomposed visually.
    """
    version_dir = PLOTS_DIR / models.classifier_version
    encoded_columns = list(model_input.columns)

    classifier_matrix = get_explainer(models.classifier).shap_values(model_input)
    if isinstance(classifier_matrix, list):
        classifier_matrix = classifier_matrix[-1]
    classifier_matrix = np.asarray(classifier_matrix)
    if classifier_matrix.ndim == 3:
        classifier_matrix = classifier_matrix[:, :, -1]

    regressor_matrix = np.asarray(get_explainer(models.regressor).shap_values(model_input))

    clf_agg_matrix, feature_names = aggregate_matrix(
        classifier_matrix, encoded_columns, CATEGORICAL_FEATURES, NUMERIC_FEATURES
    )
    reg_agg_matrix, _ = aggregate_matrix(regressor_matrix, encoded_columns, CATEGORICAL_FEATURES, NUMERIC_FEATURES)
    raw_matrix = np.array([[row.get(name) for name in feature_names] for row in raw_feature_rows], dtype=object)

    # --- Global plots ---
    plot_generator.summary_plot(clf_agg_matrix, raw_matrix, feature_names, version_dir / "global_summary_purchase_probability.png")
    plot_generator.bar_plot(clf_agg_matrix, feature_names, version_dir / "global_bar_purchase_probability.png")
    plot_generator.summary_plot(reg_agg_matrix, raw_matrix, feature_names, version_dir / "global_summary_expected_order_value.png")
    plot_generator.bar_plot(reg_agg_matrix, feature_names, version_dir / "global_bar_expected_order_value.png")

    top_features = [f["feature"] for f in classifier_global["top_features"][:DEPENDENCE_PLOT_TOP_K]]
    for feature in top_features:
        plot_generator.dependence_plot(
            feature, clf_agg_matrix, raw_matrix, feature_names, version_dir / f"global_dependence_{feature}.png"
        )

    # --- Per-customer plots (purchase-probability classifier) ---
    base_value = _base_value(models.classifier)
    for i, college_id in enumerate(college_ids):
        raw_values = [raw_feature_rows[i].get(name) for name in feature_names]
        plot_generator.waterfall_plot(
            clf_agg_matrix[i], base_value, raw_values, feature_names, version_dir / f"waterfall_college_{college_id}.png"
        )
        plot_generator.force_plot(
            clf_agg_matrix[i], base_value, raw_values, feature_names, version_dir / f"force_college_{college_id}.png"
        )
    logger.info("Generated global + per-customer (%d colleges) explainability plots -> %s", len(college_ids), version_dir)


def run_batch_scoring(
    pipeline_result: PipelineResult | None = None, engine: Engine | None = None
) -> pd.DataFrame:
    engine = engine or get_engine()
    pipeline_result = pipeline_result or MLPipeline().run()

    # Imported here (not at module top) to avoid a circular import with
    # train.py, which imports this module to refresh predictions right after training.
    from prediction.train import build_scoring_frame

    scoring_frame = build_scoring_frame(pipeline_result, engine)
    models = model_loader.load_active_models(engine, MODEL_NAME_CLASSIFIER, MODEL_NAME_REGRESSOR)

    predictions_df = inference.predict_batch(models, scoring_frame)
    model_input = inference.build_model_input(models, scoring_frame)
    raw_feature_rows = scoring_frame[ALL_FEATURES].to_dict("records")
    college_ids = scoring_frame["college_id"].tolist()

    classifier_explanations = shap_service.explain_rows(
        models.classifier, model_input, raw_feature_rows,
        categorical_cols=CATEGORICAL_FEATURES, numeric_cols=NUMERIC_FEATURES,
    )
    regressor_explanations = shap_service.explain_rows(
        models.regressor, model_input, raw_feature_rows,
        categorical_cols=CATEGORICAL_FEATURES, numeric_cols=NUMERIC_FEATURES,
    )
    classifier_global = shap_service.explain_global(
        models.classifier, model_input, categorical_cols=CATEGORICAL_FEATURES, numeric_cols=NUMERIC_FEATURES
    )
    regressor_global = shap_service.explain_global(
        models.regressor, model_input, categorical_cols=CATEGORICAL_FEATURES, numeric_cols=NUMERIC_FEATURES
    )

    write_predictions(
        engine, predictions_df, classifier_explanations, regressor_explanations,
        models.classifier_version, models.regressor_version,
    )
    write_global_importance(classifier_global, regressor_global, models.classifier_version)
    generate_plots(models, model_input, raw_feature_rows, college_ids, classifier_global)

    top = predictions_df.sort_values("expected_revenue", ascending=False).head(5)
    logger.info("Top 5 opportunities by expected revenue:\n%s", top.to_string(index=False))
    logger.info("Top global drivers of purchase probability: %s", classifier_global["top_features"][:5])

    return predictions_df


if __name__ == "__main__":
    result = run_batch_scoring()
    print(json.dumps({"colleges_scored": len(result)}, indent=2))
