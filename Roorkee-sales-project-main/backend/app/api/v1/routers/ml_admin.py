import json
import logging
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_role
from app.core import cache
from app.schemas.predictions import RetrainResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# backend/app/api/v1/routers/ml_admin.py -> repo root is 5 levels up.
REPO_ROOT = Path(__file__).resolve().parents[5]
ML_DIR = REPO_ROOT / "ml"
ML_PYTHON = ML_DIR / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

RETRAIN_TIMEOUT_SECONDS = 600


@router.post("/retrain", response_model=RetrainResponse, dependencies=[Depends(require_role("admin", "sales_manager"))])
def retrain_models() -> RetrainResponse:
    """Retrains both the purchase-propensity classifier and the expected-
    order-value regressor against the latest sales data, then immediately
    refreshes every customer's prediction.

    Runs `ml/prediction/train.py` in the ml/ project's own Python
    environment (it has pandas/scikit-learn/xgboost; the backend
    deliberately doesn't, since it only ever *reads* prediction results —
    see `predictions_service.py`). Synchronous for now: this dataset trains
    in well under a minute. A background job queue is the natural upgrade
    if training time grows (see PROJECT_SPEC.md section 11).

    Previous model versions are never deleted — see `ml/prediction/train.py`'s
    `new_version_dir()` — so this is always safe to re-run.
    """
    if not ML_PYTHON.exists():
        raise HTTPException(
            status_code=500,
            detail=f"ML environment not found at {ML_PYTHON}. Has `ml/.venv` been created and provisioned?",
        )

    logger.info("Starting model retraining via subprocess: %s -m prediction.train", ML_PYTHON)
    try:
        result = subprocess.run(
            [str(ML_PYTHON), "-m", "prediction.train"],
            cwd=str(ML_DIR),
            capture_output=True,
            text=True,
            timeout=RETRAIN_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        logger.exception("Retraining timed out after %ds", RETRAIN_TIMEOUT_SECONDS)
        raise HTTPException(status_code=504, detail="Retraining timed out") from exc

    if result.returncode != 0:
        logger.error("Retraining failed (exit %d): %s", result.returncode, result.stderr[-4000:])
        raise HTTPException(
            status_code=500,
            detail=f"Retraining failed (exit code {result.returncode}). See backend logs for the full traceback.",
        )

    summary = _parse_summary(result.stdout)
    logger.info("Retraining complete: %s", summary)
    cache.clear_all()  # fresh predictions/recommendations must be visible immediately
    return RetrainResponse(
        status="success",
        version=summary.get("version") if summary else None,
        classifier_metrics=summary.get("classifier_metrics") if summary else None,
        regressor_metrics=summary.get("regressor_metrics") if summary else None,
        predictions_written=summary.get("predictions_written") if summary else None,
        message="Models retrained and predictions refreshed."
        if summary
        else "Training completed but its summary output could not be parsed — check backend logs.",
    )


def _parse_summary(stdout: str) -> dict | None:
    """`train.py` prints one JSON object as its final line of stdout."""
    lines = [line for line in stdout.strip().splitlines() if line.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        logger.warning("Could not parse train.py's final stdout line as JSON: %s", lines[-1][:500])
        return None
