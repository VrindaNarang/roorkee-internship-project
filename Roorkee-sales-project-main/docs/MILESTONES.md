# Milestone History

A detailed, milestone-by-milestone account of what was built and why —
useful for understanding the reasoning behind a specific design decision, or
for interview prep (see also `PROJECT_SUMMARY.md`'s "Interview Talking
Points"). The root `README.md` keeps only a short summary; this file has the
full story.

## Milestone 4 — Sales Analytics Dashboard

Milestones 2–3 (real schema, CRUD, aggregation APIs) didn't exist yet when
this milestone started, so they were pulled in as prerequisites — a
dashboard can't "consume real analytics APIs" without a database behind it.

- **Data layer**
  - SQLAlchemy models: `College`, `ProductCategory`, `Product`, `SalesRep`,
    `Order`, `OrderItem` (per `PROJECT_SPEC.md` section 4, trimmed to what
    this milestone needs — no ML/RAG tables yet)
  - Alembic migration creating the full schema
  - `app/db/seed.py` — a mock data generator (Faker-based) producing ~60
    colleges, ~85 products across 6 categories, 8 sales reps, and ~1,300+
    orders over a 24-month window with seasonality, dormant accounts,
    government-vs-private payment/discount patterns, and GST-style tax
- **Backend APIs** — real, DB-backed (no more static JSON):
  - `/dashboard/*` — summary KPIs, sales trend, revenue by state, category
    distribution, top customers/products, recent orders
  - `/customers` — search, state/type/status filters, pagination, detail +
    order history
  - `/products` — search, category filter, pagination, detail + sales trend
  - `/analytics/*` — sales trend, region performance, customer insights
    (institution-type breakdown, at-risk/new-customer counts via a plain
    recency rule — not a predictive model)
- **Frontend** — React + TypeScript + MUI + Recharts + React Query:
  - Responsive app shell: collapsible sidebar, top bar with global search,
    notifications, light/dark mode toggle (persisted), user menu
  - Reusable building blocks: `KpiCard`, `ChartCard` + Recharts wrappers
    (line/bar/donut, theme-aware, CVD-safe palette), a generic `DataTable`
    (loading skeletons, empty/error states), `SearchInput`/`SelectFilter`
  - **Dashboard** — 6 KPI cards, monthly sales trend, category distribution,
    revenue by state, top 10 customers, top products, recent orders
  - **Customers** — searchable/filterable paginated list + detail page
    (profile, KPIs, full order history)
  - **Products** — searchable/filterable paginated catalog + detail page
    (KPIs, 12-month sales trend)
  - **Analytics** — revenue trend (6/12/24-month toggle), order volume,
    regional performance, customer insights
  - **Settings** — placeholder, with a working dark-mode toggle
- Verified end-to-end with a headless-browser pass over every page in both
  themes and a mobile viewport; TypeScript, ESLint, and pytest all clean.

## Milestone 5 — `ml/` feature-engineering pipeline

A standalone project (own venv) that loads straight from Postgres, cleans/
validates/deduplicates it, engineers RFM/tenure/seasonality/trend features,
and writes model-ready datasets to `ml/datasets/`. Run via
`python run_pipeline.py`.

## Milestone 6 — Customer Health Score

An explainable, weighted 0-100 score (**not** an ML model, by design) over
ten factors — see `backend/app/health_score/`. New APIs under
`/customers/health`, `/customers/critical`, `/customers/healthy`,
`/customers/at-risk`. The Customers page and Dashboard show health score,
risk band (green/amber/red), and trend for every customer.

## Milestone 7 — Purchase Propensity Prediction

Two XGBoost models (`ml/prediction/`) — a classifier for "will this college
buy in the next 30 days" and a regressor for "how much, if they do" —
trained with a proper train/val/test split, cross-validated hyperparameter
search, and versioned artifacts (previous versions are never deleted). New
APIs under `/predictions/*` and `POST /ml/retrain`. A new **Sales
Opportunities** dashboard page ranks every customer by expected revenue,
filterable by state/customer type/probability/expected revenue.

## Milestone 8 — Explainable AI (SHAP)

`ml/explainability/` (`explainer.py` caches a `shap.TreeExplainer` per
model, `utils.py` aggregates one-hot dummy-column contributions back to
human-readable original features — exact, not approximate, since SHAP
values are additive — and phrases them as plain-English "reasons",
`shap_service.py` is the per-row/global API, `plot_generator.py` renders
waterfall/force/summary/bar/dependence plots to PNG). Every prediction
carries its top-5 contributing factors (signed value + direction, split
positive/negative) plus 3-5 reason sentences (e.g. "Payment delayed by 18
days"), computed by `ml/prediction/predict.py` during batch scoring. The
Customer Health Score — a weighted formula, not an ML model — gets the same
reason-sentence treatment from its own exact per-factor attribution
(`backend/app/health_score/explanations.py`). Four endpoints (`GET
/explain/customer/{id}`, `/explain/global`, `/explain/top-features`,
`/explain/model-summary`) serve all of this; plot PNGs are served directly
from `ml/artifacts/prediction/plots/` via a `StaticFiles` mount at
`/plots/...` (the backend never touches `shap`/`matplotlib`). The Customer
Detail page is tabbed (Overview / Explainability); the Explainability tab
shows health score, purchase probability, and expected order value each
with their reasons, factor chips, and (for purchase probability) waterfall
+ force plot images.

## Milestone 9 — Business Recommendation Engine

Rule-based, not ML/LLM-based — `backend/app/recommendation_engine/`
(`config.py` tunable thresholds, `rules.py` seven business rules across
four types, condition-vs-scoring split into `priority_engine.py`,
`recommendation_service.py` assembles signals from
`HealthScoreService`/`predictions_service`/orders and is the only piece
that touches Postgres). Nothing is persisted — every recommendation is
recomputed live from already-persisted health scores/predictions/orders, so
it's always in sync. Customer rule: "Contact {name} this week" above a
purchase-probability floor, High priority exactly when probability > 85%
AND health score > 70 (the milestone's literal example). Risk rules: health
score < 40, or no purchase in 180+ days. Regional rules: revenue down > 15%
(campaign) or up > 20% (opportunity) over a 90-day window. Sales rules:
next-30-days expected revenue vs. last month's actual, ±10%. Five endpoints
(`GET /recommendations`, `/recommendations/customers`,
`/recommendations/regions`, `/recommendations/high-priority`,
`/recommendations/risk`) and a **Recommendations** dashboard page (KPI row,
a cross-type "Suggested Actions" feed, and High Priority Customers /
Critical Customers / Regional Opportunities / Revenue Alerts sections).

## Milestone 10 — Embedded AI Sales Copilot

No RAG, no FAISS, no vector database, no Claude/OpenAI, no separate AI
Assistant page. `backend/app/copilot/` — `intent_router.py`
deterministically matches a question to one of 9 intents via regex (not LLM
function-calling, which free-tier models support inconsistently);
`tool_executor.py` calls this backend's *own* REST endpoints over an
in-process ASGI transport (never Postgres/the ORM directly);
`prompt_builder.py` assembles a system prompt + the retrieved JSON +
conversation history; `llm_provider.py` wraps any OpenAI-compatible
chat-completions API (Groq → OpenRouter → Ollama, auto-selected by which
API key is set); `response_formatter.py` appends a deterministic "Data
Sources" footer built from the *actual* endpoints called, never from what
the LLM claims; `copilot_service.py` orchestrates all of it and reports
honestly if the LLM itself is unreachable rather than inventing an answer.
One endpoint, `POST /copilot/chat`, streams the answer as plain text. The
frontend adds a collapsible **Sales Copilot** panel at the bottom of the
**Analytics** page — suggested-question chips, streamed responses via
`fetch` + `ReadableStream`, a typing-dots loading animation, copy-response
and clear-conversation controls. Conversation history is kept client-side
only (sent with each request) — no new database tables.

## Milestone 11 — Enterprise Production Readiness

The feature set was complete after Milestone 10; this milestone is entirely
about hardening it, not adding business features. Highlights:

- **Authentication & RBAC** — JWT bearer auth (`backend/app/auth/`), three
  fixed roles (admin/sales_manager/sales_executive), every endpoint
  protected except login, two write endpoints role-restricted, a full
  Login page + `AuthContext` + `ProtectedRoute` on the frontend.
- **Standardized error handling** — every error response, from any router,
  now has the same `{detail, error_code, request_id}` shape
  (`app/core/exception_handlers.py`); a request-ID + access-log middleware
  (`app/core/middleware.py`) traces every request end-to-end.
- **Performance** — an in-process TTL cache (`app/core/cache.py`) on every
  aggregation-heavy read path; route-level code splitting + vendor chunking
  on the frontend (`React.lazy`, `vite.config.ts`'s `manualChunks`).
- **Testing** — a `Login.tsx` full-page test, an `auth_headers` pytest
  fixture, dedicated test files for auth/caching/error-envelope behavior,
  and a from-scratch frontend testing setup (Vitest + React Testing
  Library) with tests for utilities, components, and hooks.
- **Docker** — multi-stage `Dockerfile`s (`dev`/`production` targets) for
  both services, a production `docker-compose.prod.yml` (nginx-served
  static frontend, multi-worker backend, non-root users, healthchecks).
- **A real bug fix, found by this hardening pass:** `GET
  /predictions/feature-importance` had been silently 500ing since Milestone
  8 changed the shape of the file it read — the Sales Opportunities page's
  "What's Driving Purchase Likelihood" chart was broken in a way that
  hadn't been noticed. Removed the dead endpoint and switched the frontend
  to the correct, already-built `/explain/top-features` endpoint.
- **Dead code removal** — two never-implemented placeholder packages
  (`app/ml/`, `app/rag/`), a hardcoded fake `/settings/profile` stub that
  ignored who was actually logged in, and the broken feature-importance
  endpoint above.
- **Documentation** — this file, plus `docs/ARCHITECTURE.md`,
  `docs/API.md`, `docs/DEPLOYMENT.md`, `docs/SETUP.md`,
  `docs/ENVIRONMENT_VARIABLES.md`, `docs/DEVELOPER_GUIDE.md`,
  `docs/PROJECT_STRUCTURE.md`, and `PROJECT_SUMMARY.md`.
