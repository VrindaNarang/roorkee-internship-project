# Architecture

SalesPilot AI is a modular monorepo with four independently runnable
projects, each with a single clear responsibility:

```
┌────────────────────┐  HTTPS   ┌──────────────────────────────────────────┐
│   React Frontend    │ ───────► │              FastAPI Backend              │
│  (MUI + Recharts)   │ ◄─────── │  REST API · Auth (JWT) · domain services  │
└────────────────────┘          │  Sales Copilot (intent routing + LLM)     │
                                 └───────┬────────────────────────────────┘
                                         │ SQLAlchemy
                                         ▼
                             ┌───────────────────────┐
                             │      PostgreSQL         │
                             │  transactional store   │
                             └───────────────────────┘
                                         ▲
                                         │ batch writes (predictions,
                                         │ health scores, SHAP explanations)
                             ┌───────────────────────────────────────────┐
                             │            Offline ML Pipeline (ml/)        │
                             │  feature engineering → XGBoost training →   │
                             │  SHAP explainer fit → versioned artifacts   │
                             └───────────────────────────────────────────┘
```

## The four projects

| Project | Language / stack | Owns | Never touches |
|---|---|---|---|
| `frontend/` | React 18 + TypeScript + MUI + Recharts + React Query | UI, client-side auth state, routing | Postgres directly — always goes through the backend API |
| `backend/` | FastAPI + SQLAlchemy 2 + Pydantic v2 | REST API, auth, request validation, business-rule engines (health score, recommendations, Sales Copilot), read/write to Postgres | Model training — it only *loads* versioned artifacts the `ml/` project already produced |
| `ml/` | Python + pandas + XGBoost + SHAP + matplotlib (own venv) | Feature engineering, model training, batch scoring, SHAP explainability, plot generation | The live API — it writes predictions/plots to Postgres/disk and exits; it's never itself a long-running server |
| `docs/` + root `.md` files | Markdown | Everything you're reading now | — |

Each has its own dependency set and can be developed/tested in isolation —
notably, `backend/` never installs pandas/xgboost/shap (it only *reads*
their output), which keeps the API's container image small and its
dependency surface auditable.

## Why this shape

- **Backend as the single integration point.** The frontend never talks to
  Postgres or an LLM provider directly — everything goes through the FastAPI
  backend. This keeps security (auth, CORS, API-key custody) in one place.
- **ML training is offline, inference is online.** Training XGBoost models
  and fitting SHAP explainers happens in batch (`ml/` scripts, triggered
  manually or via `POST /api/v1/ml/retrain`). The backend only *loads*
  versioned artifacts and runs fast inference — it never trains a model
  inside a request handler.
- **The Sales Copilot calls this backend's own REST API, never SQL
  directly.** A deterministic, regex-based intent router picks which of
  this API's own endpoints to call; only the resulting JSON is handed to an
  LLM. No RAG, no vector database, no NL-to-SQL — see
  [PROJECT_SPEC.md §8](../PROJECT_SPEC.md#8-sales-copilot-integration).
- **Everything that isn't a pure database read is a "business-rule engine",
  not a black box.** Customer Health Score is a transparent weighted
  formula (not an ML model — see §6a). Purchase predictions come with SHAP
  explanations attached. Recommendations come from readable IF/THEN rules,
  not a model. This is the "Explainable AI" half of the product's identity.

## Request lifecycle (a typical authenticated GET)

1. Browser sends `GET /api/v1/customers/42` with `Authorization: Bearer <jwt>`.
2. `RequestContextMiddleware` (`app/core/middleware.py`) assigns/reuses a
   request ID and starts a timer.
3. `CORSMiddleware` validates the request's origin against
   `BACKEND_CORS_ORIGINS`.
4. FastAPI resolves the route inside the *protected* router group
   (`app/api/v1/api.py`), which runs `get_current_user` (`app/auth/
   dependencies.py`) first — decodes the JWT, loads the `User` row, 401s if
   invalid/expired.
5. The route handler calls a service function (e.g.
   `customers_service.get_customer_detail(db, 42)`), passing the request's
   own `Session` (`Depends(get_db)`).
6. The service runs SQLAlchemy queries and returns a plain dict or ORM
   object; the router's `response_model` (a Pydantic schema) validates and
   serializes it.
7. On any exception, one of three handlers
   (`app/core/exception_handlers.py`) converts it into the standard
   `{"detail": ..., "error_code": ..., "request_id": ...}` envelope.
8. `RequestContextMiddleware` logs one line (`METHOD path -> status (Xms)
   [request_id]`) and stamps the same ID onto the response's
   `X-Request-ID` header.

## The Sales Copilot pipeline (Milestone 10)

```
question ──► intent_router (regex, no LLM) ──► tool_executor
                                                  │ (in-process ASGI call
                                                  │  into this same API,
                                                  │  forwarding the asking
                                                  │  user's own JWT)
                                                  ▼
                                          backend REST endpoints
                                          (analytics/predictions/
                                           health/explain/recs)
                                                  │
                                                  ▼
                                          prompt_builder assembles
                                          {system prompt, retrieved JSON,
                                           history} ──► LLM provider
                                          (Groq → OpenRouter → Ollama)
                                                  │
                                                  ▼
                                          response_formatter appends a
                                          verified "Data Sources" footer
                                          (built from what was actually
                                           called, never from what the
                                           LLM claims)
```

See `PROJECT_SPEC.md §8` for the full design rationale.

## Data flow: from mock orders to an explained prediction

1. `backend/app/db/seed.py` generates mock colleges/products/orders directly
   into Postgres.
2. `ml/run_pipeline.py` reads those same tables, engineers RFM/tenure/
   seasonality/trend features, and writes model-ready datasets.
3. `ml/prediction/train.py` trains two XGBoost models (purchase-probability
   classifier, expected-order-value regressor), fits a SHAP `TreeExplainer`
   per model, and writes: (a) `predictions` rows with a `shap_explanation`
   JSON column, (b) `model_registry` metadata, (c) plot PNGs to
   `ml/artifacts/prediction/plots/<version>/`.
4. The backend's `predictions_service` / `explainability_service` /
   `recommendation_service` read those rows live on every API request — no
   separate "sync" step. A short in-process TTL cache (`app/core/cache.py`)
   absorbs bursts of near-simultaneous requests without going stale for
   more than ~30 seconds.

## Authentication & authorization

Three fixed roles — `admin`, `sales_manager`, `sales_executive`
(`app/models/user.py`). JWT bearer tokens (`app/auth/security.py`), no
refresh-token rotation, no OAuth/SSO — this is internal software with a
small, known user base, not a consumer product. Every endpoint except
`POST /api/v1/auth/login` and `GET /health` requires a valid token
(enforced once, at the router-group level — see `app/api/v1/api.py`).
Two write/trigger endpoints (`POST /ml/retrain`, `POST /customers/health`)
additionally require `admin` or `sales_manager` via
`Depends(require_role(...))`; everything else is readable by any
authenticated role.

## Performance & caching

- **`app/core/cache.py`** — a minimal in-process TTL cache (no Redis; this
  backend runs as a single logical service, so a process-local cache is
  simpler and sufficient). Applied to the aggregation-heavy read paths:
  dashboard summaries, analytics, product listings, and the health-score/
  recommendation engines' per-college signal computation. 20-30 second TTL,
  invalidated immediately after a retrain/recalculate write.
- **Route-level code splitting** (frontend) — every page is a separate
  lazy-loaded chunk (`React.lazy` + `Suspense`, see `routes/AppRoutes.tsx`),
  and vendor libraries (React, MUI, Recharts, React Query) are split into
  their own cacheable bundles (`vite.config.ts`'s `manualChunks`).

## Testing strategy

- **Backend** (`backend/tests/`) — pytest against a real Postgres (the same
  one `docker-compose.yml` provisions), using `TestClient`. Pure-logic
  modules (health-score scoring, recommendation rules, Copilot intent
  routing) get direct unit tests with no DB/HTTP involved; cross-cutting
  concerns (auth, error envelopes, caching) get their own focused suites.
- **Frontend** (`frontend/src/**/*.test.{ts,tsx}`) — Vitest + React Testing
  Library. Utility functions, presentational components, hooks (with mocked
  API calls), and one full-page test (`Login.tsx`, covering the
  authentication flow's UI).
- **ML** (`ml/tests/`) — pytest for feature-engineering functions and the
  explainability aggregation/phrasing utilities.

See `docs/DEVELOPER_GUIDE.md` for how to run each suite.
