import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.exception_handlers import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.db import seed
from app.db.session import SessionLocal

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

if settings.plots_dir:
    PLOTS_DIR = Path(settings.plots_dir)
else:
    # backend/app/main.py -> repo root is 2 levels up. Only valid when `ml/`
    # and `backend/` are sibling folders on the same filesystem (local dev,
    # or a container with `ml/artifacts` volume-mounted at this exact
    # relative position) — see `PLOTS_DIR` setting for the container case.
    REPO_ROOT = Path(__file__).resolve().parents[2]
    PLOTS_DIR = REPO_ROOT / "ml" / "artifacts" / "prediction" / "plots"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("%s starting up in '%s' mode", settings.project_name, settings.environment)

    # Auto-populate a brand-new (empty) database on first boot — see
    # `app.db.seed.bootstrap_if_empty` — so the app is fully demo-ready
    # without a manual seed command. No-op once data already exists.
    db = SessionLocal()
    try:
        if seed.bootstrap_if_empty(db):
            logger.info("Auto-seed populated the database on startup")
    except Exception:
        logger.exception("Auto-seed on startup failed — continuing with an empty/partial database")
    finally:
        db.close()

    yield
    logger.info("%s shutting down", settings.project_name)


app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description=(
        "Explainable-AI-powered Sales Intelligence CRM API. See /docs for the interactive "
        "reference — every endpoint except /health and /api/v1/auth/login requires a bearer "
        "token (POST /api/v1/auth/login to obtain one)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Runs "inside" CORS (added after it) so request-ID/logging wraps every
# request including ones CORS would otherwise short-circuit for OPTIONS.
app.add_middleware(RequestContextMiddleware)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "environment": settings.environment}


# Serves the SHAP plot PNGs `ml/prediction/predict.py` generates — the
# backend never generates or touches these images itself, only serves
# what's already on disk (see PROJECT_SPEC.md section 6a). Best-effort: a
# missing/unwritable plots directory (e.g. a misconfigured PLOTS_DIR in a
# container) shouldn't take down the whole API — explainability images are a
# secondary feature, not core functionality. `/plots/...` requests just 404
# if this mount never happens.
try:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/plots", StaticFiles(directory=str(PLOTS_DIR)), name="plots")
except OSError:
    logger.warning("Could not create/access PLOTS_DIR (%s) — /plots/* will 404 until this is fixed", PLOTS_DIR)

app.include_router(api_router, prefix=settings.api_v1_prefix)
