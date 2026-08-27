"""Model registry access + artifact loading.

The `model_registry` table (see PROJECT_SPEC.md section 4.2) is the single
source of truth for "which version is active" — artifacts on disk are never
deleted (Milestone 7 requires keeping previous versions), so rolling back is
just flipping `is_active` back to an older row, no re-training required.

No ORM models are imported here on purpose: `ml/` and `backend/` are separate
Python environments, so this talks to the table via plain SQL through the
same SQLAlchemy engine `preprocessing.loaders` already uses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import xgboost as xgb
from sqlalchemy import Engine, text

from preprocessing.encoding import FeatureEncoder
from utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class RegistryEntry:
    model_name: str
    model_type: str
    version: str
    artifact_path: str
    metrics: dict
    is_active: bool


def register_model(
    engine: Engine, *, model_name: str, model_type: str, version: str, artifact_path: Path, metrics: dict
) -> None:
    """Inserts a new active version and deactivates every prior version of
    the same `model_name` — all in one transaction.
    """
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE model_registry SET is_active = false WHERE model_name = :model_name"),
            {"model_name": model_name},
        )
        conn.execute(
            text(
                """
                INSERT INTO model_registry
                    (model_name, model_type, version, trained_at, metrics, artifact_path, is_active)
                VALUES
                    (:model_name, :model_type, :version, now(), CAST(:metrics AS JSON), :artifact_path, true)
                """
            ),
            {
                "model_name": model_name,
                "model_type": model_type,
                "version": version,
                "metrics": json.dumps(metrics),
                "artifact_path": str(artifact_path),
            },
        )
    logger.info("Registered %s version %s as active (artifact: %s)", model_name, version, artifact_path)


def get_active_entry(engine: Engine, model_name: str) -> RegistryEntry | None:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT model_name, model_type, version, artifact_path, metrics, is_active
                FROM model_registry
                WHERE model_name = :model_name AND is_active = true
                ORDER BY trained_at DESC
                LIMIT 1
                """
            ),
            {"model_name": model_name},
        ).first()
    if row is None:
        return None
    return RegistryEntry(
        model_name=row.model_name,
        model_type=row.model_type,
        version=row.version,
        artifact_path=row.artifact_path,
        metrics=row.metrics if isinstance(row.metrics, dict) else json.loads(row.metrics),
        is_active=row.is_active,
    )


@dataclass
class LoadedModels:
    classifier: xgb.XGBClassifier
    regressor: xgb.XGBRegressor
    encoder: FeatureEncoder
    classifier_version: str
    regressor_version: str


def load_active_models(engine: Engine, classifier_name: str, regressor_name: str) -> LoadedModels:
    clf_entry = get_active_entry(engine, classifier_name)
    reg_entry = get_active_entry(engine, regressor_name)
    if clf_entry is None or reg_entry is None:
        raise RuntimeError(
            f"No active model found for '{classifier_name}' and/or '{regressor_name}' — run train.py first."
        )

    clf_dir = Path(clf_entry.artifact_path)
    reg_dir = Path(reg_entry.artifact_path)

    classifier = xgb.XGBClassifier()
    classifier.load_model(clf_dir / "classifier_model.json")

    regressor = xgb.XGBRegressor()
    regressor.load_model(reg_dir / "regressor_model.json")

    # Both models come from the same training run and share one directory
    # (and therefore one fitted encoder) — see train.py's `save_artifacts`.
    encoder = FeatureEncoder.load(clf_dir / "encoder.joblib")

    return LoadedModels(
        classifier=classifier,
        regressor=regressor,
        encoder=encoder,
        classifier_version=clf_entry.version,
        regressor_version=reg_entry.version,
    )
