from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration, sourced from environment variables / .env.

    See PROJECT_SPEC.md section 1.2 for why config lives here rather than being
    scattered across modules.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"

    project_name: str = "SalesPilot AI"
    api_v1_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql+psycopg2://salespilot:salespilot_dev_password@127.0.0.1:5433/salespilot"
    )

    backend_cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Where `ml/prediction/predict.py`'s SHAP plot PNGs live (see
    # PROJECT_SPEC.md §6a). Empty by default, which means "derive it from
    # this file's location assuming the standard repo layout" (local dev,
    # `ml/` and `backend/` as sibling folders) — see `app/main.py`. Set this
    # explicitly in containerized deployments, where that relative-path
    # assumption doesn't hold (the backend image doesn't contain a `ml/`
    # sibling folder; a volume gets mounted at whatever path this points to).
    plots_dir: str = ""

    # --- Auth (Milestone 11) ---
    # Default is fine for local dev only — every deployment MUST override this
    # via .env; `get_settings()` is `lru_cache`d so a real value must be set
    # before the first request, not patched in later.
    jwt_secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # one working day


@lru_cache
def get_settings() -> Settings:
    return Settings()
