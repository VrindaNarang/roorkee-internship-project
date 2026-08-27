import json
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.health_score.config import MODEL_VERSION as HEALTH_SCORE_MODEL_VERSION
from app.health_score.explanations import build_health_score_reasons
from app.health_score.health_service import HealthScoreService
from app.health_score.weights import WEIGHTS as HEALTH_SCORE_WEIGHTS
from app.schemas.explainability import (
    ContributorOut,
    CustomerExplanation,
    GlobalExplanation,
    GlobalModelExplanation,
    ModelExplanation,
    ModelSummaryEntry,
    ModelSummaryResponse,
    TopFeaturesResponse,
)
from app.services import predictions_service

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _prediction_artifacts_dir() -> Path:
    """Mirrors `app.main`'s `PLOTS_DIR` resolution (settings override, else
    the sibling-`ml/`-folder default) so this file and the plot mount always
    agree on where `ml/prediction/predict.py`'s output actually lives —
    `global_feature_importance.json` sits next to `plots/` in that same
    `prediction/` directory."""
    plots_dir = get_settings().plots_dir
    if plots_dir:
        return Path(plots_dir).parent
    return REPO_ROOT / "ml" / "artifacts" / "prediction"


def _global_importance_path() -> Path:
    return _prediction_artifacts_dir() / "global_feature_importance.json"

CLASSIFIER_MODEL_NAME = "purchase_propensity_classifier"
REGRESSOR_MODEL_NAME = "expected_order_value_regressor"


def _active_model_version(db: Session, model_name: str) -> str | None:
    row = db.execute(
        text(
            "SELECT version FROM model_registry WHERE model_name = :name AND is_active = true "
            "ORDER BY trained_at DESC LIMIT 1"
        ),
        {"name": model_name},
    ).first()
    return row.version if row else None


def _plot_url(version: str | None, filename: str) -> str | None:
    if version is None:
        return None
    return f"/plots/{version}/{filename}"


def _health_score_explanation(db: Session, college_id: int) -> ModelExplanation | None:
    health = HealthScoreService(db).get_for_customer(college_id)
    if health is None:
        return None

    # `contribution` (normalized_score * weight) is always >= 0 — it's a
    # weighted formula, not a signed SHAP value, so a "below-average" factor
    # still contributes *something* positive to the total. To get a
    # correctly-signed value (negative contributors must show as negative),
    # we measure each factor relative to its own neutral midpoint (a 50/100
    # normalized score) rather than relative to zero: `weight * (score - 50)`.
    # This is exactly `contribution - weight * 50`.
    breakdown = health["component_breakdown"]
    signed: dict[str, float] = {
        f: round(d["contribution"] - d["weight"] * 50, 4) for f, d in breakdown.items()
    }
    positive = [
        ContributorOut(feature=f, value=v, direction="increases") for f, v in signed.items() if v >= 0
    ]
    negative = [
        ContributorOut(feature=f, value=v, direction="decreases") for f, v in signed.items() if v < 0
    ]
    positive.sort(key=lambda c: abs(c.value), reverse=True)
    negative.sort(key=lambda c: abs(c.value), reverse=True)

    return ModelExplanation(
        value=health["health_score"],
        positive_contributors=positive,
        negative_contributors=negative,
        reasons=build_health_score_reasons(breakdown),
        confidence=None,  # deterministic formula — not a probabilistic estimate
    )


def _fetch_raw_shap_explanation(db: Session, college_id: int, prediction_type: str) -> dict | None:
    """Reads the `shap_explanation` JSON `ml/prediction/predict.py` persisted
    for this customer/model directly, rather than going through
    `predictions_service` (which flattens it to a bare contributor list and
    drops the business-friendly `reasons` the ml/ side already computed).
    """
    row = db.execute(
        text(
            "SELECT shap_explanation FROM predictions WHERE college_id = :college_id "
            "AND prediction_type = :prediction_type ORDER BY prediction_date DESC LIMIT 1"
        ),
        {"college_id": college_id, "prediction_type": prediction_type},
    ).first()
    if row is None or row.shap_explanation is None:
        return None
    raw = row.shap_explanation
    return raw if isinstance(raw, dict) else json.loads(raw)


def _prediction_explanation(
    raw_explanation: dict | None,
    value: float,
    confidence: float | None,
    version: str | None,
    plot_filenames: dict[str, str],
) -> ModelExplanation | None:
    if raw_explanation is None:
        return None
    positive = [ContributorOut(**c) for c in raw_explanation.get("positive_contributors", [])]
    negative = [ContributorOut(**c) for c in raw_explanation.get("negative_contributors", [])]
    plot_urls = {
        name: url for name, filename in plot_filenames.items() if (url := _plot_url(version, filename))
    }
    return ModelExplanation(
        value=value,
        positive_contributors=positive,
        negative_contributors=negative,
        reasons=raw_explanation.get("reasons", []),
        confidence=confidence,
        plot_urls=plot_urls,
    )


def get_customer_explanation(db: Session, college_id: int) -> CustomerExplanation | None:
    college = db.execute(text("SELECT name FROM colleges WHERE id = :id"), {"id": college_id}).first()
    if college is None:
        return None

    prediction = predictions_service.get_for_customer(db, college_id)
    classifier_version = _active_model_version(db, CLASSIFIER_MODEL_NAME)

    purchase_probability = None
    expected_order_value = None
    if prediction is not None:
        purchase_probability = _prediction_explanation(
            _fetch_raw_shap_explanation(db, college_id, "purchase_probability"),
            prediction.purchase_probability,
            prediction.confidence_score,
            classifier_version,
            {
                "waterfall": f"waterfall_college_{college_id}.png",
                "force": f"force_college_{college_id}.png",
            },
        )
        expected_order_value = _prediction_explanation(
            _fetch_raw_shap_explanation(db, college_id, "expected_order_value"),
            prediction.expected_order_value,
            None,
            None,
            {},
        )

    return CustomerExplanation(
        college_id=college_id,
        name=college.name,
        health_score=_health_score_explanation(db, college_id),
        purchase_probability=purchase_probability,
        expected_order_value=expected_order_value,
        overall_confidence=prediction.confidence_score if prediction else None,
        generated_at=prediction.prediction_date if prediction else None,
    )


def _load_global_importance() -> dict | None:
    path = _global_importance_path()
    if not path.exists():
        return None
    return json.loads(path.read_text())


def get_global_explanation(db: Session) -> GlobalExplanation | None:
    payload = _load_global_importance()
    if payload is None:
        return None
    version = payload["model_version"]

    def _model_explanation(key: str, plot_filenames: dict[str, str]) -> GlobalModelExplanation:
        block = payload[key]
        plot_urls = {name: url for name, fn in plot_filenames.items() if (url := _plot_url(version, fn))}
        ranked_features = [{**f, "rank": i + 1} for i, f in enumerate(block["top_features"])]
        return GlobalModelExplanation(
            top_features=ranked_features, summary_text=block["summary_text"], plot_urls=plot_urls
        )

    return GlobalExplanation(
        generated_at=payload["generated_at"],
        model_version=version,
        purchase_probability=_model_explanation(
            "purchase_probability",
            {
                "summary": "global_summary_purchase_probability.png",
                "bar": "global_bar_purchase_probability.png",
            },
        ),
        expected_order_value=_model_explanation(
            "expected_order_value",
            {
                "summary": "global_summary_expected_order_value.png",
                "bar": "global_bar_expected_order_value.png",
            },
        ),
    )


def get_top_features(model: str = "purchase_probability", limit: int = 10) -> TopFeaturesResponse | None:
    payload = _load_global_importance()
    if payload is None or model not in payload:
        return None
    features = payload[model]["top_features"][:limit]
    return TopFeaturesResponse(
        model=model,
        top_features=[
            {"feature": f["feature"], "mean_abs_contribution": f["mean_abs_contribution"], "rank": i + 1}
            for i, f in enumerate(features)
        ],
    )


def get_model_summary(db: Session) -> ModelSummaryResponse:
    def _entry(model_name: str) -> ModelSummaryEntry | None:
        row = db.execute(
            text(
                "SELECT model_name, model_type, version, trained_at, metrics FROM model_registry "
                "WHERE model_name = :name AND is_active = true ORDER BY trained_at DESC LIMIT 1"
            ),
            {"name": model_name},
        ).first()
        if row is None:
            return None
        metrics = row.metrics if isinstance(row.metrics, dict) else json.loads(row.metrics)
        return ModelSummaryEntry(
            model_name=row.model_name, model_type=row.model_type, version=row.version,
            trained_at=row.trained_at, metrics=metrics,
        )

    return ModelSummaryResponse(
        purchase_propensity_classifier=_entry(CLASSIFIER_MODEL_NAME),
        expected_order_value_regressor=_entry(REGRESSOR_MODEL_NAME),
        customer_health_score={
            "model_version": HEALTH_SCORE_MODEL_VERSION,
            "model_type": "weighted_formula",
            "note": "Not an ML model — a transparent, weighted 0-100 formula. See PROJECT_SPEC.md section 6a.",
            "weights": HEALTH_SCORE_WEIGHTS,
        },
    )
