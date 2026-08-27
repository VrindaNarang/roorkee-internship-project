"""Trains the Purchase Propensity classifier and Expected Order Value
regressor, evaluates both on a held-out test set, and persists a new
versioned model.

    Regenerate datasets -> join health score -> split (train/val/test)
    -> hyperparameter-tune + cross-validate -> fit -> evaluate -> persist
    -> register in Postgres -> refresh predictions

Run with:
    cd ml
    .venv/Scripts/python.exe -m prediction.train
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.model_selection import GridSearchCV, StratifiedKFold, KFold, train_test_split
from sqlalchemy import Engine, text

from pipeline import MLPipeline, PipelineResult
from prediction import evaluate, model_loader
from prediction.config import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    CLASSIFICATION_TARGET,
    DEFAULT_HEALTH_SCORE,
    MODEL_NAME_CLASSIFIER,
    MODEL_NAME_REGRESSOR,
    NUMERIC_FEATURES,
    REGRESSION_TARGET,
    SEARCH,
    SPLIT,
    new_version_dir,
)
from preprocessing.encoding import FeatureEncoder
from preprocessing.loaders import get_engine
from utils.logging_utils import get_logger

logger = get_logger(__name__)


def join_health_scores(df: pd.DataFrame, engine: Engine) -> pd.DataFrame:
    """Left-joins each college's latest health score onto `df`.

    Colleges with no health score computed yet (e.g. onboarded after the
    last `POST /customers/health` run) fall back to a neutral default rather
    than being dropped — a missing health score isn't evidence of anything.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT DISTINCT ON (college_id) college_id, health_score
                FROM customer_health_scores
                ORDER BY college_id, score_date DESC
                """
            )
        ).all()
    health_by_college = {r.college_id: r.health_score for r in rows}

    df = df.copy()
    df["health_score"] = df["college_id"].map(health_by_college).fillna(DEFAULT_HEALTH_SCORE)
    n_missing = (~df["college_id"].isin(health_by_college)).sum()
    if n_missing:
        logger.info(
            "%d/%d colleges had no health score yet — defaulted to %.0f",
            n_missing,
            len(df),
            DEFAULT_HEALTH_SCORE,
        )
    return df


def build_training_frame(pipeline_result: PipelineResult, engine: Engine) -> pd.DataFrame:
    """Training frame: features computed *as of the 30-day-ago cutoff*, plus
    both targets observed in the (cutoff, now] window that followed — see
    `pipeline.py`'s `generate_datasets` for why that split keeps this leakage-free.
    """
    df = pipeline_result.purchase_prediction_dataset.copy()
    return join_health_scores(df, engine)


def build_scoring_frame(pipeline_result: PipelineResult, engine: Engine) -> pd.DataFrame:
    """Inference frame: features computed *as of right now* — used to predict
    the genuinely-unknown next 30 days, as opposed to the training frame
    which is deliberately stale by 30 days so a label was observable.
    """
    df = pipeline_result.customer_health_dataset.copy()
    return join_health_scores(df, engine)


def _encode_split(
    encoder: FeatureEncoder, df: pd.DataFrame
) -> pd.DataFrame:
    encoded = encoder.transform(df[["college_id", *ALL_FEATURES]])
    feature_cols = encoder.one_hot.get_feature_names_out(encoder.categorical_cols).tolist() + [
        f"{c}_scaled" for c in encoder.numeric_cols
    ]
    return encoded[feature_cols]


def train_classifier(train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame, encoder: FeatureEncoder):
    X_train, y_train = _encode_split(encoder, train_df), train_df[CLASSIFICATION_TARGET]
    X_val, y_val = _encode_split(encoder, val_df), val_df[CLASSIFICATION_TARGET]
    X_test, y_test = _encode_split(encoder, test_df), test_df[CLASSIFICATION_TARGET]

    base = xgb.XGBClassifier(random_state=SPLIT.random_state, eval_metric="logloss")
    cv = StratifiedKFold(n_splits=SPLIT.cv_folds_classifier, shuffle=True, random_state=SPLIT.random_state)
    search = GridSearchCV(base, SEARCH.classifier_grid, scoring="roc_auc", cv=cv, n_jobs=-1)
    logger.info(
        "Tuning classifier over %d hyperparameter combinations via %d-fold CV",
        _grid_size(SEARCH.classifier_grid),
        SPLIT.cv_folds_classifier,
    )
    search.fit(X_train, y_train)
    best = search.best_estimator_
    logger.info("Best classifier params: %s (CV ROC-AUC=%.4f)", search.best_params_, search.best_score_)

    val_metrics = evaluate.evaluate_classifier(y_val.values, best.predict(X_val), best.predict_proba(X_val)[:, 1])
    test_metrics = evaluate.evaluate_classifier(y_test.values, best.predict(X_test), best.predict_proba(X_test)[:, 1])

    metrics = {
        "best_params": search.best_params_,
        "cv_roc_auc": search.best_score_,
        "validation": val_metrics,
        "test": test_metrics,
    }
    return best, metrics


def train_regressor(train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame, encoder: FeatureEncoder):
    X_train, y_train = _encode_split(encoder, train_df), train_df[REGRESSION_TARGET]
    X_val, y_val = _encode_split(encoder, val_df), val_df[REGRESSION_TARGET]
    X_test, y_test = _encode_split(encoder, test_df), test_df[REGRESSION_TARGET]

    base = xgb.XGBRegressor(random_state=SPLIT.random_state)
    cv = KFold(n_splits=SPLIT.cv_folds_regressor, shuffle=True, random_state=SPLIT.random_state)
    search = GridSearchCV(base, SEARCH.regressor_grid, scoring="neg_mean_absolute_error", cv=cv, n_jobs=-1)
    logger.info("Tuning regressor over %d hyperparameter combinations via %d-fold CV",
                _grid_size(SEARCH.regressor_grid), SPLIT.cv_folds_regressor)
    search.fit(X_train, y_train)
    best = search.best_estimator_
    logger.info("Best regressor params: %s (CV MAE=%.2f)", search.best_params_, -search.best_score_)

    val_metrics = evaluate.evaluate_regressor(y_val.values, best.predict(X_val))
    test_metrics = evaluate.evaluate_regressor(y_test.values, best.predict(X_test))

    metrics = {
        "best_params": search.best_params_,
        "cv_mae": -search.best_score_,
        "validation": val_metrics,
        "test": test_metrics,
    }
    return best, metrics


def _grid_size(grid: dict) -> int:
    size = 1
    for values in grid.values():
        size *= len(values)
    return size


def save_artifacts(
    version_dir: Path,
    encoder: FeatureEncoder,
    classifier: xgb.XGBClassifier,
    regressor: xgb.XGBRegressor,
    classifier_metrics: dict,
    regressor_metrics: dict,
) -> None:
    version_dir.mkdir(parents=True, exist_ok=True)
    encoder.save(version_dir / "encoder.joblib")
    classifier.save_model(version_dir / "classifier_model.json")
    regressor.save_model(version_dir / "regressor_model.json")
    (version_dir / "classifier_metrics.json").write_text(json.dumps(classifier_metrics, indent=2, default=str))
    (version_dir / "regressor_metrics.json").write_text(json.dumps(regressor_metrics, indent=2, default=str))
    (version_dir / "feature_columns.json").write_text(
        json.dumps({"numeric": NUMERIC_FEATURES, "categorical": CATEGORICAL_FEATURES}, indent=2)
    )
    logger.info("Saved model artifacts to %s", version_dir)


def run_training() -> dict:
    logger.info("=== Purchase Propensity training run starting ===")
    engine = get_engine()

    logger.info("Regenerating feature-engineered datasets (Milestone 5 pipeline)...")
    pipeline_result = MLPipeline().run()

    df = build_training_frame(pipeline_result, engine)
    logger.info("Training frame: %d colleges, %d positive labels (%.1f%%)",
                len(df), df[CLASSIFICATION_TARGET].sum(), df[CLASSIFICATION_TARGET].mean() * 100)

    # --- Classification split: train / val / test, stratified on the label ---
    train_val_df, test_df = train_test_split(
        df, test_size=SPLIT.test_size, stratify=df[CLASSIFICATION_TARGET], random_state=SPLIT.random_state
    )
    train_df, val_df = train_test_split(
        train_val_df,
        test_size=SPLIT.val_size,
        stratify=train_val_df[CLASSIFICATION_TARGET],
        random_state=SPLIT.random_state,
    )
    logger.info("Classification split: train=%d, val=%d, test=%d", len(train_df), len(val_df), len(test_df))

    # Encoder is fit on the TRAINING split only — val/test must never
    # influence how categories/scaling are learned, or the held-out
    # evaluation would be quietly leaked.
    encoder = FeatureEncoder(CATEGORICAL_FEATURES, NUMERIC_FEATURES).fit(train_df[ALL_FEATURES])

    classifier, classifier_metrics = train_classifier(train_df, val_df, test_df, encoder)

    # --- Regression split: purchasers-only subset (see train.py module docstring) ---
    purchasers = df[df[CLASSIFICATION_TARGET] == 1]
    logger.info("Regression training subset (purchasers only): %d colleges", len(purchasers))
    reg_train_val, reg_test = train_test_split(purchasers, test_size=SPLIT.test_size, random_state=SPLIT.random_state)
    reg_train, reg_val = train_test_split(reg_train_val, test_size=SPLIT.val_size, random_state=SPLIT.random_state)
    logger.info("Regression split: train=%d, val=%d, test=%d", len(reg_train), len(reg_val), len(reg_test))

    regressor, regressor_metrics = train_regressor(reg_train, reg_val, reg_test, encoder)

    version, version_dir = new_version_dir()
    save_artifacts(version_dir, encoder, classifier, regressor, classifier_metrics, regressor_metrics)

    model_loader.register_model(
        engine,
        model_name=MODEL_NAME_CLASSIFIER,
        model_type="xgboost_classifier",
        version=version,
        artifact_path=version_dir,
        metrics=classifier_metrics,
    )
    model_loader.register_model(
        engine,
        model_name=MODEL_NAME_REGRESSOR,
        model_type="xgboost_regressor",
        version=version,
        artifact_path=version_dir,
        metrics=regressor_metrics,
    )

    logger.info("=== Training run %s complete — refreshing predictions ===", version)
    from prediction import predict as predict_module

    predictions_df = predict_module.run_batch_scoring(pipeline_result=pipeline_result, engine=engine)

    return {
        "version": version,
        "classifier_metrics": classifier_metrics,
        "regressor_metrics": regressor_metrics,
        "predictions_written": len(predictions_df),
    }


if __name__ == "__main__":
    summary = run_training()
    # Single line, deliberately — callers (e.g. the backend's POST /ml/retrain,
    # which invokes this script as a subprocess) parse the LAST line of
    # stdout as JSON; pretty-printing would spread it across many lines.
    print(json.dumps(summary, default=str))
