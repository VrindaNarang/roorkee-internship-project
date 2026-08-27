# Project Structure

```
sales_ai_internship_project/
├── PROJECT_SPEC.md            # single source of truth for architecture/design decisions
├── PROJECT_SUMMARY.md          # resume/interview/demo-ready project summary
├── README.md                   # start here
├── docker-compose.yml           # local dev stack (hot-reload)
├── docker-compose.prod.yml      # production-like stack (nginx + multi-worker backend)
├── .env.example                 # copy to .env at the repo root
│
├── docs/                       # this file, ARCHITECTURE.md, DEPLOYMENT.md, etc.
│
├── backend/                    # FastAPI service — see below
├── frontend/                   # React + Vite SPA — see below
├── ml/                          # offline ML pipeline — own venv — see below
├── data/                        # raw / processed / mock data (gitignored)
├── infra/                       # deployment scripts (placeholder)
└── rag/                         # NOT BUILT — see PROJECT_SPEC.md §4.3/§8;
                                  # superseded by the Sales Copilot (backend/app/copilot/)
```

## `backend/` — FastAPI service

```
backend/
├── app/
│   ├── main.py                  # app assembly: middleware, exception handlers, router mount
│   ├── core/
│   │   ├── config.py              # Settings (env-var driven), one process-wide instance
│   │   ├── logging.py             # stdout logging setup
│   │   ├── middleware.py          # request-ID + access-log middleware
│   │   ├── exception_handlers.py  # standardized {detail, error_code, request_id} envelope
│   │   └── cache.py                # in-process TTL cache for expensive reads
│   ├── auth/                      # JWT auth: security.py (hashing/tokens), auth_service.py,
│   │   │                          # dependencies.py (get_current_user, require_role)
│   ├── db/                        # session.py, base.py, seed.py (mock data), seed_users.py
│   ├── models/                    # SQLAlchemy ORM: College, Order, Product, User, etc.
│   ├── schemas/                   # Pydantic request/response models, one file per domain
│   ├── services/                  # query/business logic per domain (dashboard, customers,
│   │   │                          # products, analytics, predictions, explainability)
│   ├── health_score/               # Milestone 6 — weighted, explainable health-score engine
│   │   │                          # (config/weights/scoring/health_service/explanations)
│   ├── recommendation_engine/      # Milestone 9 — rule-based recommendations
│   │   │                          # (config/rules/priority_engine/recommendation_service)
│   ├── copilot/                    # Milestone 10 — Sales Copilot
│   │   │                          # (config/llm_provider/tool_executor/intent_router/
│   │   │                          #  prompt_builder/response_formatter/copilot_service)
│   └── api/v1/
│       ├── api.py                  # router registry — auth is public, everything else
│       │                          # is mounted behind get_current_user once
│       └── routers/                # one thin file per domain: auth, dashboard, customers,
│                                   # products, analytics, predictions, explain,
│                                   # recommendations, copilot, ml_admin
├── alembic/                       # migrations (colleges/products/orders/health_scores/
│                                  # predictions/model_registry/users)
├── tests/                          # pytest — one file per concern (auth, cache, health,
│                                  # recommendation_engine, copilot)
├── requirements.txt / requirements-dev.txt
├── pytest.ini
└── Dockerfile                      # multi-stage: `dev` and `production` targets
```

**Rule of thumb:** routers are thin (parse request → call one service
function → return); all real logic lives in `services/` or one of the three
domain-engine packages (`health_score/`, `recommendation_engine/`,
`copilot/`), each of which follows the same internal shape: a `config.py`
for tunable thresholds, pure-math/pure-logic modules with no I/O, and one
service module that's the only thing allowed to touch the database or an
external API.

## `frontend/` — React SPA

```
frontend/
├── src/
│   ├── main.tsx / App.tsx          # bootstrap: QueryClient, ThemeModeProvider,
│   │                              # BrowserRouter, AuthProvider, ErrorBoundary
│   ├── routes/AppRoutes.tsx        # route table — public (Login) vs protected
│   │                              # (everything else, behind <ProtectedRoute>);
│   │                              # every page is React.lazy-loaded
│   ├── pages/                      # one file per route: Dashboard, Customers(+Detail),
│   │                              # Products(+Detail), Analytics (embeds the Copilot
│   │                              # panel), SalesOpportunities, Recommendations,
│   │                              # Settings, Login, NotFound, Forbidden
│   ├── components/
│   │   ├── layout/                  # Sidebar, Topbar, Layout (responsive app shell)
│   │   ├── auth/                    # ProtectedRoute
│   │   ├── dashboard/, charts/, table/, filters/, common/
│   │   ├── health/, predictions/, recommendations/, copilot/
│   ├── context/                    # AuthContext, ThemeModeContext
│   ├── api/                        # axios client + one typed module per domain
│   ├── hooks/                      # React Query hooks, one file per domain
│   ├── utils/format.ts             # currency/date/number formatting (en-IN locale)
│   ├── theme/                      # MUI theme (light/dark palettes)
│   └── test/setup.ts               # Vitest + Testing Library setup
├── vite.config.ts                  # build + vitest config, manual vendor chunking
├── nginx.conf                      # SPA-fallback + caching rules for the production image
└── Dockerfile                       # multi-stage: `dev` and `production` (nginx) targets
```

**Convention:** every page follows the same shape — React Query hooks for
data, `DataTable`/`ChartCard`/`KpiCard` for consistent loading/empty/error
states, `StatusChip` for enum-like values, `formatCurrency`/`formatDate`
from `utils/format.ts`. New pages should reuse these rather than
reinventing a loading spinner or empty state.

## `ml/` — offline ML pipeline (own Python venv)

```
ml/
├── preprocessing/, features/, pipeline.py     # Milestone 5: feature engineering
├── prediction/                                # Milestone 7: train.py, predict.py, inference.py
├── explainability/                             # Milestone 8: SHAP explainer/service/plots
│   │                                          # (explainer.py, utils.py, shap_service.py,
│   │                                          #  plot_generator.py, config.py)
├── artifacts/                                   # versioned models + plots (gitignored)
├── tests/                                       # pytest for feature engineering + explainability
└── run_pipeline.py                              # CLI entrypoint
```

This project is deliberately isolated from `backend/` — it has its own
`requirements.txt` (pandas, scikit-learn, xgboost, shap, matplotlib) and its
own venv, so the backend's dependency footprint stays small. The backend
only ever *reads* what this pipeline writes (Postgres rows + plot PNGs), and
triggers a re-run via `POST /api/v1/ml/retrain`, which shells out to
`ml/prediction/train.py` in a subprocess.
