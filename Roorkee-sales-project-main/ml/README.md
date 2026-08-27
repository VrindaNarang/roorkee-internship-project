# SalesPilot AI — Feature Engineering & ML Data Pipeline

**Status: Milestone 5 — Feature Engineering & ML Data Pipeline.** This module
turns the raw Postgres tables (colleges, products, orders, order items) into
clean, feature-rich datasets ready for future ML models. No models are
trained here — see [What's not here yet](#whats-not-here-yet).

## Setup

```bash
cd ml
python -m venv .venv
./.venv/Scripts/activate        # Windows (PowerShell: .venv\Scripts\Activate.ps1)
# source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
```

Reads the same root `.env` the backend uses (`DATABASE_URL`) — no separate
config needed, as long as Postgres is up and seeded (see the repo root
README's Milestone 4 instructions).

## Run the pipeline

```bash
python run_pipeline.py
```

Load Data → Preprocess → Engineer Features → Generate ML Dataset → Save,
logging what happened at every stage (rows dropped, outliers capped, dates
coerced, features built). Outputs land in `datasets/`:

| File | Grain | Purpose |
|---|---|---|
| `customer_health_score_dataset(_encoded).csv` | 1 row / college | Future input to a customer-health/churn model |
| `purchase_prediction_dataset(_encoded).csv` | 1 row / college | Future input to a next-purchase classifier; includes a non-leaky `purchased_in_next_30_days` label |
| `product_features_dataset.csv` | 1 row / product | Popularity/revenue-contribution features, e.g. for future cross-sell |

The `_encoded` files are the model-ready variant (categoricals one-hot
encoded, numerics standard-scaled); the plain files are human-readable, for
inspection.

## Folder structure

```
ml/
├── config/               settings.py — DB URL, business-calendar constants
├── utils/                logging_utils.py — shared pipeline logger
├── preprocessing/         loaders.py (DB -> DataFrames), cleaning.py (missing
│                         values, dedup, dtype validation, invalid dates),
│                         outliers.py (fit/transform IQR capping),
│                         encoding.py (fit/transform one-hot + scaling)
├── feature_engineering/   time_features.py, customer_features.py,
│                         sales_features.py, product_features.py
├── datasets/              pipeline output (gitignored, regenerate via
│                         run_pipeline.py)
├── artifacts/preprocessing/  saved outlier bounds (JSON), for reuse at
│                         inference time
├── tests/                 pytest unit tests, one file per module
├── pipeline.py             MLPipeline orchestrator class
└── run_pipeline.py         CLI entrypoint
```

Every preprocessing step is a stateless `DataFrame -> DataFrame` function or
an explicit fit/transform/save/load class (`OutlierCapper`,
`FeatureEncoder`) — the same code path runs at training time and will run at
inference time later, with fitted bounds/encoders reloaded from
`artifacts/preprocessing/` instead of refit.

## Tests

```bash
pytest -q
```

## What's not here yet

Per `PROJECT_SPEC.md` section 12 and this milestone's explicit scope:

- ML model training (XGBoost next-purchase / health-score models)
- SHAP explainability
- Model registry / scoring job
- AI Assistant (RAG chatbot)

See `PROJECT_SPEC.md` section 6 for the full ML pipeline roadmap.
