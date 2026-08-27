# SalesPilot AI — Project Specification

**Status:** Draft v1.0 — awaiting approval before implementation begins
**Owner:** Vrinda Narang
**Last updated:** 2026-07-01

This document is the single source of truth for SalesPilot AI. No implementation
should begin until this spec is reviewed and approved. Any deviation from this
spec during implementation should be reflected back into this file so it never
goes stale.

---

## 0. Executive Summary

SalesPilot AI is an Explainable-AI-powered Sales Intelligence and Conversational
CRM platform for a laboratory equipment company selling chemical/lab equipment
to colleges (government and private). It combines:

- **Business intelligence** — dashboards, KPIs, trend analysis over historical orders
- **Predictive ML** — next-purchase prediction, customer health/churn scoring
- **Explainable AI** — SHAP-based explanations attached to every prediction
- **Conversational AI** — a Sales Copilot, embedded in the Analytics dashboard,
  that answers natural-language business questions by calling this backend's
  own REST APIs (analytics, predictions, health scores, SHAP explanations,
  recommendations) and handing only that retrieved data to a free
  OpenAI-compatible LLM (Groq/OpenRouter/Ollama). No RAG, no vector database,
  no document ingestion, no direct database access from the LLM's side —
  see section 8.
- **Recommendation engine** — "who to contact this week," cross-sell suggestions,
  churn-risk alerts

The system is built as a modular monorepo, containerized with Docker Compose,
with clearly separated frontend, backend, and ML training concerns so each
can be developed and tested independently.

---

## 1. System Architecture

### 1.1 High-level component diagram (described)

```
┌────────────────────┐        ┌──────────────────────────────────────────┐
│   React Frontend    │ HTTPS  │              FastAPI Backend              │
│  (MUI + Recharts)   │◄──────►│  - REST API (v1)                          │
└────────────────────┘        │  - Auth (JWT)                             │
                               │  - Domain services (colleges, products,  │
                               │    orders, dashboard, health, insights)   │
                               │  - ML inference layer (loads artifacts)   │
                               │  - Sales Copilot (intent routing + REST   │
                               │    calls into this same API, then a free  │
                               │    OpenAI-compatible LLM — see §8)        │
                               └───────┬────────────────────────────────────┘
                                       │
                                       ▼
                         ┌───────────────────────┐
                         │      PostgreSQL        │
                         │  transactional store   │
                         └───────────────────────┘
                                       ▲
                     │ batch writes (predictions, health scores, insights)
                     │
         ┌───────────────────────────────────────────────────────────────┐
         │                   Offline ML Pipeline (ml/)                    │
         │  Mock data gen → feature engineering → XGBoost training →      │
         │  SHAP explainer fit → model registry (versioned artifacts)     │
         └───────────────────────────────────────────────────────────────┘

         ┌───────────────────────────────────────────────────────────────┐
         │              Background Job Runner (Celery + Redis)*           │
         │  CSV import processing · scheduled insight generation ·        │
         │  scheduled model scoring · document embedding ingestion        │
         └───────────────────────────────────────────────────────────────┘
```
\* Not in the originally listed stack — proposed addition, see §12.

### 1.2 Why this shape

- **Backend as the single integration point.** Frontend never talks to Postgres
  or an LLM provider directly — everything goes through FastAPI. This keeps
  security (auth, query constraints, API-key custody) in one place.
- **ML training is offline, inference is online.** Training XGBoost models and
  fitting SHAP explainers happens in batch (`ml/` scripts, run manually or on a
  schedule). The backend only *loads* versioned artifacts and runs fast
  inference — it never trains models inside a request.
- **The Sales Copilot calls this backend's own REST API, never SQL directly
  (Milestone 10; supersedes the RAG/LangChain/FAISS plan below).** A
  deterministic, keyword-based intent router picks which of this API's own
  endpoints to call (analytics, predictions, health scores, SHAP
  explanations, recommendations); only that retrieved JSON is handed to the
  LLM. No vector database, no document ingestion, no NL-to-SQL — see §8.

---

## 2. Modules (detailed)

| Module | Responsibility |
|---|---|
| **Auth** ✅ | JWT login/session, role-based access (admin, sales_manager, sales_executive) — implemented Milestone 11 |
| **Data Import** | CSV upload, validation, staging, ETL into normalized tables, job status tracking |
| **Master Data** | CRUD for colleges (customers), products, categories, sales reps |
| **Orders** | Order + order-line CRUD, payment status tracking |
| **Dashboard/KPIs** | Aggregated metrics: revenue, order volume, growth %, region/category breakdowns |
| **Prediction Service** | Serves next-purchase and churn predictions from trained models |
| **Customer Health Scoring** | RFM + model-based composite health score per college, time series |
| **Explainability (XAI)** | SHAP value computation, storage, and API exposure per prediction |
| **Insights Engine** | Scheduled anomaly/trend detection + LLM-phrased narrative insights |
| **Recommendation Engine** | Contact-priority lists, cross-sell suggestions, at-risk alerts |
| **Sales Copilot** | Business-question chat embedded in Analytics; intent routing + backend API calls + free LLM phrasing (no RAG/documents/vector DB) |
| **Model Registry** | Tracks trained model versions, metrics, active/inactive status |
| **Admin** | User management, model retrain triggers, import job monitoring |

---

## 3. Folder Structure (design only — not yet created)

```
sales_ai_internship_project/
├── PROJECT_SPEC.md
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── README.md
│
├── frontend/
│   ├── src/
│   │   ├── api/            # typed API client wrappers
│   │   ├── components/     # shared UI components
│   │   ├── pages/          # route-level pages (see §11)
│   │   ├── charts/         # Recharts wrapper components
│   │   ├── hooks/
│   │   ├── context/        # auth context, theme context
│   │   ├── routes/
│   │   └── utils/
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/     # colleges, products, orders, dashboard,
│   │   │                       # predictions, health_scores, insights,
│   │   │                       # recommendations, copilot, auth, admin
│   │   ├── core/                # config, security, dependencies
│   │   ├── db/                  # session, base, alembic migrations
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic request/response models
│   │   ├── services/             # business logic per domain
│   │   ├── ml/                   # inference wrappers loading versioned artifacts
│   │   ├── health_score/          # Milestone 6 — weighted health-score engine
│   │   ├── recommendation_engine/ # Milestone 9 — rule-based recommendations
│   │   ├── copilot/                # Milestone 10 — Sales Copilot (not "rag/" — see below)
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
│
├── ml/
│   ├── data_generation/          # mock data generator (colleges, products, orders)
│   ├── feature_engineering/
│   ├── training/                 # train_purchase_predictor.py, train_health_score.py
│   ├── explainability/           # SHAP fitting + serialization utilities
│   ├── evaluation/
│   ├── artifacts/                # versioned model files (gitignored)
│   └── notebooks/
│
├── rag/                            # NOT BUILT — superseded by Milestone 10's
│   ├── ingestion/                 # Sales Copilot (app/copilot/), which calls this
│   ├── embeddings/                # backend's own REST API instead of RAG/FAISS/a
│   ├── vector_store/              # vector store. Left here only as a record of the
│   └── documents/                 # original draft plan — see §4.3 and §8.
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── mock/
│
├── infra/
│   ├── docker/                   # per-service Dockerfiles
│   └── scripts/
│
└── docs/
    ├── architecture/              # diagrams
    └── api/                       # generated API reference
```

---

## 4. PostgreSQL Database Schema

### 4.1 Core entities

**users** ✅ *(Milestone 11 — implemented as described, with two field-name
and one enum-value deviation: `full_name` not `name`, `hashed_password` not
`password_hash` — matching this codebase's naming elsewhere — and the third
role is `sales_executive`, not `sales_rep`, per Milestone 11's literal
brief)*
`id, email (unique), hashed_password, full_name, role [admin|sales_manager|sales_executive], is_active, created_at`

**colleges** (the customer entity)
`id, name, institution_type [government|private], region, state, city, address, contact_name, contact_email, contact_phone, onboarded_date, status [active|dormant], created_at, updated_at`

**product_categories**
`id, name, description`

**products**
`id, sku (unique), name, category_id → product_categories, unit_price, cost_price, unit_of_measure, is_active, created_at`

**sales_reps**
`id, name, email, region, hire_date`

**orders**
`id, order_number (unique), college_id → colleges, sales_rep_id → sales_reps, order_date, status [pending|fulfilled|cancelled], payment_status [paid|pending|overdue], payment_due_date, payment_received_date, discount_pct, subtotal, tax_amount, total_amount, created_at`

**order_items**
`id, order_id → orders, product_id → products, quantity, unit_price, discount_pct, line_total`

**payments**
`id, order_id → orders, amount, payment_date, method, status [completed|partial|failed]`

### 4.2 ML / Analytics entities

**customer_health_scores** *(as implemented, Milestone 6)*
`id, college_id → colleges, score_date, health_score (0-100), health_status [healthy|at_risk|critical], rfm_recency, rfm_frequency, rfm_monetary, component_breakdown (JSONB — full per-factor weighted breakdown), model_version`

**predictions** *(as implemented, Milestone 7)*
`id, college_id → colleges, prediction_type [purchase_probability|expected_order_value], predicted_value, probability (nullable, only set for purchase_probability rows), prediction_date, model_version, shap_explanation (JSONB, reserved — null until the SHAP milestone)`

**insights**
`id, insight_type, title, description, related_entity_type, related_entity_id, severity [info|warning|critical], generated_at, generated_by [rule|model|llm]`

**model_registry**
`id, model_name, model_type, version, trained_at, metrics (JSONB), artifact_path, is_active`

### 4.3 RAG / Chat entities — not built (superseded by Milestone 10)

The original plan below (documents/chunks/FAISS/chat_sessions) was never
implemented. Milestone 10's brief explicitly rules out RAG, FAISS, and a
vector database, and the Sales Copilot it builds instead is stateless
server-side — conversation history is kept client-side only and sent with
each request, so **no new tables exist for it at all**. If durable,
cross-session chat history is wanted later, `chat_sessions`/`chat_messages`
(without the `documents`/`document_chunks` half) could still be added then.

~~**documents**~~
~~`id, title, file_path, doc_type, uploaded_by → users, uploaded_at`~~

~~**document_chunks**~~
~~`id, document_id → documents, chunk_text, chunk_index, faiss_vector_id`~~
~~*(the embedding vector itself lives in the FAISS index on disk; this table maps FAISS ids back to source text/document for citation)*~~

~~**chat_sessions**~~
~~`id, user_id → users, title, started_at`~~

~~**chat_messages**~~
~~`id, session_id → chat_sessions, role [user|assistant], content, retrieved_sources (JSONB), created_at`~~

### 4.4 Operational entities

**data_import_jobs**
`id, file_name, uploaded_by → users, status [pending|processing|completed|failed], rows_processed, rows_failed, error_log, started_at, completed_at`

### 4.5 Relationships summary

- `colleges (1) — (N) orders` — a college places many orders
- `orders (1) — (N) order_items`, `products (1) — (N) order_items` — line items join orders and products
- `product_categories (1) — (N) products`
- `sales_reps (1) — (N) orders`
- `orders (1) — (N) payments` — supports partial/delayed payments
- `colleges (1) — (N) customer_health_scores` — time series, one row per scoring run
- `colleges (1) — (N) predictions`, `products (0..1) — (N) predictions`
- `users (1) — (N) data_import_jobs`
- (no chat/document relationships — see §4.3: not built, superseded by Milestone 10's stateless Sales Copilot)

All foreign keys use `ON DELETE RESTRICT` for transactional data (orders, order_items)
and `ON DELETE CASCADE` for dependent child records with no independent meaning
(e.g. `order_items` when their parent `order` is deleted).

---

## 5. Backend API Design (FastAPI, `/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | Authenticate (OAuth2 password grant), issue JWT *(Milestone 11)* |
| GET | `/auth/me` | Current user profile *(Milestone 11)* |
| POST | `/data/import/csv` | Upload CSV, kick off async import job |
| GET | `/data/import/jobs/{id}` | Import job status |
| GET/POST | `/colleges` | List (filter/paginate) / create colleges |
| GET/PUT/DELETE | `/colleges/{id}` | Retrieve/update/deactivate a college |
| GET | `/colleges/{id}/orders` | Order history for a college |
| GET | `/colleges/{id}/health-score` | Latest + historical health score |
| GET/POST | `/products` | List / create products |
| GET/PUT/DELETE | `/products/{id}` | Product detail management |
| GET | `/products/{id}/sales-trend` | Time-series sales for a product |
| GET/POST | `/orders` | List / create orders |
| GET | `/orders/{id}` | Order detail with line items |
| GET | `/dashboard/summary` | Top-line KPIs (revenue, orders, growth) |
| GET | `/dashboard/sales-trend?range=` | Time-series revenue/orders |
| GET | `/dashboard/region-performance` | Region breakdown |
| GET | `/dashboard/top-products` | Best/worst performing products |
| GET | `/customers/health` | Latest health score (+ trend) for every customer *(Milestone 6)* |
| GET | `/customers/{id}/health` | Health score detail + full factor breakdown for one customer *(Milestone 6)* |
| GET | `/customers/critical` / `/customers/healthy` / `/customers/at-risk` | Customers in each health band *(Milestone 6)* |
| POST | `/customers/health` | Trigger a full health-score recalculation *(Milestone 6)* |
| GET | `/predictions/customers` | All customers' current predictions, ranked + filterable *(Milestone 7)* |
| GET | `/predictions/customer/{id}` | Purchase probability + expected order value (+ SHAP explanation) for one college *(Milestone 7/8)* |
| GET | `/predictions/high-probability` | Customers most likely to buy in the next 30 days *(Milestone 7)* |
| GET | `/predictions/top-opportunities` | Customers ranked by expected revenue *(Milestone 7)* |
| GET | `/predictions/feature-importance` | Global "what's driving purchase likelihood" (aggregated SHAP) *(Milestone 8)* |
| POST | `/ml/retrain` | Retrain both prediction models + refresh all predictions + SHAP explanations *(Milestone 7/8)* |
| GET | `/insights` | Latest generated insights feed |
| GET | `/recommendations` | Every recommendation (customer/risk/regional/sales), ranked by priority *(Milestone 9)* |
| GET | `/recommendations/customers` | "Contact this week" recommendations *(Milestone 9)* |
| GET | `/recommendations/regions` | Regional revenue-swing recommendations *(Milestone 9)* |
| GET | `/recommendations/high-priority` | Every high-priority recommendation, any type *(Milestone 9)* |
| GET | `/recommendations/risk` | Dormant/low-health-score follow-up recommendations *(Milestone 9)* |
| POST | `/copilot/chat` | Sales Copilot — streamed, grounded business-question answer *(Milestone 10)* |

Rows above marked with a milestone are implemented as described. Unmarked rows
(insights) are still the original draft — not yet built. The `/chat/sessions`
+ `/documents` draft rows (session-based chat + RAG document management) were
superseded entirely by `/copilot/chat` — Milestone 10 rules out RAG/documents/
a vector database and doesn't persist chat sessions server-side at all (see
§4.3 and §8). The recommendation-engine paths were superseded by Milestone 9's actual brief
(rule-based customer/risk/regional/sales recommendations, not a contact-list +
cross-sell pair) — see section 9 below. The original draft paths for predictions/models
(`/predictions/next-purchases`, `/predictions/run`, `/models`,
`/models/retrain`) were superseded by the paths above when Milestone 7 was
actually implemented — see section 6a below for why (two separate XGBoost
models rather than one, and `predicted_value`/`probability` split by
`prediction_type` rather than a single next-purchase-date prediction).

All list endpoints support pagination (`limit`/`offset`), filtering, and sorting
as query params. Write endpoints are role-gated (sales_rep is read-mostly;
sales_manager/admin can trigger imports, retraining, and manage documents).

---

## 6. ML Pipeline

1. **Mock data generation** (`ml/data_generation/`) — produces 500 colleges,
   100 products, 20,000+ orders over 3 years, with seasonal demand curves,
   repeat vs. dormant customer behavior, government/private mix, payment
   delays, and discounting patterns (see §13 for detailed generation rules).
2. **Feature engineering** (`ml/feature_engineering/`) — builds per-college and
   per-college-product features: RFM (recency/frequency/monetary), order
   growth trend, seasonality indicators, category mix, payment delay history,
   institution type, region.
3. **Training** (`ml/training/`)
   - **Next-purchase model** — XGBoost regressor/classifier predicting
     likelihood and expected timing/value of a customer's next order.
   - **Customer health / churn model** — XGBoost classifier trained against a
     defined "dormant" label (e.g., no order in N days relative to historical
     cadence), producing a health score.
4. **Explainability fitting** (`ml/explainability/`) — fits a SHAP
   `TreeExplainer` against each trained model at training time; explainer
   artifact is versioned alongside the model.
5. **Model registry** — each training run writes model + explainer artifacts
   to `ml/artifacts/<model_name>/<version>/`, and registers metadata (metrics,
   version, timestamp) in the `model_registry` table. Backend loads only the
   artifact marked `is_active`.
6. **Scoring** — batch scoring job (triggered via `/predictions/run` or on a
   schedule) runs inference across all colleges/products, computes SHAP values
   per prediction, and writes results + explanations into `predictions` and
   `customer_health_scores`.

### 6a. Implementation notes (Milestones 5-8) — deviations from the plan above

- **Customer Health Score (Milestone 6) is *not* an ML model.** Per that
  milestone's explicit brief, it's a transparent weighted formula over ten
  normalized factors (`backend/app/health_score/weights.py` +
  `config.py`) — deliberately explainable by construction (every score comes
  with its full per-factor breakdown) rather than a trained classifier. If a
  learned health/churn model is wanted later, it can be trained against this
  same `customer_health_scores` history as a label source.
- **Purchase Propensity (Milestone 7) uses two separate XGBoost models**
  (`ml/prediction/`) rather than one regressor/classifier hybrid: an
  `XGBClassifier` for `purchased_in_next_30_days` and an `XGBRegressor` for
  `next_order_value` (trained only on customers who did purchase — a
  standard two-part/hurdle formulation). `expected_revenue` exposed by the
  API is `probability x expected_order_value`, computed at read time.
- **Model artifacts** live at `ml/artifacts/prediction/<version>/` (one
  shared directory per training run holding both models + the fitted
  feature encoder), rather than one directory per model name — since both
  models are always trained together from the same feature set and share
  one encoder.
- **`POST /ml/retrain`** runs `ml/prediction/train.py` as a subprocess in the
  `ml/` project's own Python environment (which has pandas/scikit-learn/
  xgboost) rather than inside the backend process — the backend only ever
  *reads* the `predictions` table, so it never needs those dependencies.
- **SHAP explainability (Milestone 8) lives in `ml/explainability/`** — split
  into `config.py` (paths/constants), `explainer.py` (a process-wide
  `id(model)`-keyed cache so `shap.TreeExplainer` is fitted once per model,
  not once per call), `utils.py` (dummy-column aggregation + business-friendly
  phrase templates), `shap_service.py` (the high-level per-row/global API
  `ml/prediction/predict.py` calls), and `plot_generator.py` (headless
  matplotlib, saves waterfall/force/summary/bar/dependence PNGs). SHAP values
  are aggregated from one-hot dummy columns back to the *original* feature
  (e.g. `state_Maharashtra` + `state_Gujarat` + ... → `state`) since SHAP
  values are additive — a sales manager shouldn't see dummy columns. Only the
  top 5 contributors per prediction are persisted (not the full feature
  vector) to keep `shap_explanation` small, but each row also carries 3-5
  plain-English `reasons` sentences (e.g. "Payment delayed by 18 days")
  generated from per-feature phrase templates, not raw SHAP numbers. Global
  "what's driving this overall" is *not* computed by aggregating those
  truncated per-row top-5 lists (that would undercount features that weren't
  in everyone's top 5) — it's computed once from the full SHAP matrix during
  batch scoring and written to
  `ml/artifacts/prediction/global_feature_importance.json`, which the
  backend reads directly (no DB table needed for a value that's really just
  a derived summary of the current model). Plot PNGs are written to
  `ml/artifacts/prediction/plots/<model_version>/` and served by the backend
  via a `StaticFiles` mount at `/plots/...` — the backend never generates or
  touches these images, only serves what ml/ already produced.
- **Customer Health Score explanations reuse the same presentation, not the
  same math.** Health score is a weighted formula (not an ML model — see
  above), so `backend/app/health_score/explanations.py` treats
  `component_breakdown` as its own exact attribution: `contribution - weight *
  50` gives each factor a correctly-signed value relative to its own neutral
  midpoint (since raw `contribution` is always ≥ 0), then phrases it with the
  same "+ / -" sentence style SHAP explanations use, so all three "models" read
  consistently in the UI.

---

## 7. Explainable AI (XAI) Integration

**Status: implemented (Milestone 8) for all three models — purchase
propensity classifier, expected-order-value regressor, and customer health
score.**

- ✅ Every prediction row stores a `shap_explanation` JSON payload: top 5
  contributing features (split into `positive_contributors` /
  `negative_contributors`, signed values + direction) plus plain-English
  `reasons` sentences — see `predictions.shap_explanation`, populated by
  `ml/prediction/predict.py` via `ml/explainability/shap_service.py`.
- ✅ **Local explainability API** — four endpoints under `/api/v1/explain/`
  (`backend/app/api/v1/routers/explain.py` +
  `backend/app/services/explainability_service.py`):
  - `GET /explain/customer/{id}` — health score, purchase probability, and
    expected order value for one customer, each with contributors, reasons,
    confidence, and plot image URLs.
  - `GET /explain/global` — aggregated SHAP feature importance + summary text
    for both prediction models, read from
    `ml/artifacts/prediction/global_feature_importance.json`.
  - `GET /explain/top-features?model=&limit=` — ranked feature-importance
    list for either model.
  - `GET /explain/model-summary` — active model versions/metrics for all
    three "models" (including the health-score formula's weights).
- ✅ **Visualizations** — `ml/explainability/plot_generator.py` generates
  waterfall, force, summary (beeswarm), bar, and dependence plots as PNGs
  under `ml/artifacts/prediction/plots/<model_version>/`, served by the
  backend at `/plots/...` (FastAPI `StaticFiles`, no ML dependencies added to
  the backend).
- ✅ **Frontend** — `CustomerDetail.tsx` is now tabbed (Overview /
  Explainability). The Explainability tab consumes
  `useCustomerExplanation(id)` and renders, per model: the predicted value,
  color-coded "+ / -" reason sentences, chip lists of top positive/negative
  factors, and (for purchase probability) the waterfall + force plot images.
- ✅ Global feature importance also powers the existing "what's driving
  purchase likelihood overall" view on the **Sales Opportunities** page.
- ✅ **Feeding XAI into the Copilot** — the `GET /explain/customer/{id}`
  endpoint is one of the Sales Copilot's tools (Milestone 10, §8): questions
  like "explain why ABC College has a low health score" resolve the customer,
  call this endpoint, and hand its contributors/reasons to the LLM to phrase
  in plain business language.
- ⬜ **A dedicated global-explainability dashboard page** (summary/bar plots,
  full feature-importance ranking) — the backend/`ml/` side is fully built
  (`GET /explain/global`, `GET /explain/top-features`) but no frontend page
  consumes them yet beyond the Sales Opportunities page's existing view.

---

## 8. Sales Copilot Integration

**Status: implemented (Milestone 10).** This section fully supersedes the
original "RAG Chatbot Integration" plan — that design (LangChain agent,
Claude, FAISS document retrieval, persisted chat sessions) is explicitly
ruled out by Milestone 10's brief. What's built instead is deliberately
lighter: no vector database, no document ingestion, no direct database
access from the LLM's side, and no server-side chat-session persistence.

### 8.1 Architecture

`backend/app/copilot/` (mirrors the `health_score/`/`recommendation_engine/`
separation-of-concerns convention):

- **`config.py`** — LLM provider credentials/selection, sourced from `.env`.
- **`llm_provider.py`** — a thin wrapper around *any* OpenAI-compatible
  chat-completions endpoint. Groq, OpenRouter, and Ollama all speak that same
  wire format, so one class covers all three; only `base_url`/`api_key`/
  `model` differ. `get_llm_provider()` auto-selects the first provider with a
  configured API key in preference order (Groq → OpenRouter → Ollama, the
  last needing no key at all), or an explicit `COPILOT_LLM_PROVIDER` override
  — switching providers is a `.env` change, not a code change. No Claude, no
  OpenAI's own hosted API — both explicitly ruled out.
- **`intent_router.py`** — **deterministic keyword/regex matching, not LLM
  function-calling.** Free-tier models have inconsistent tool-calling
  support, so the exact same question always triggers the exact same backend
  calls: auditable, testable, and immune to the LLM inventing a tool that
  doesn't exist.
- **`tool_executor.py`** — calls this backend's *own* REST API (`/dashboard/*`,
  `/analytics/*`, `/predictions/*`, `/customers/*`, `/explain/*`,
  `/recommendations/*`) over an in-process ASGI transport (`httpx.
  ASGITransport`, no real TCP round trip). **Never touches PostgreSQL or the
  ORM directly** — it only knows REST paths and gets back exactly the JSON a
  real API caller would see, using the exact same routing/serialization every
  other client goes through.
- **`prompt_builder.py`** — builds the message list handed to the LLM: a
  system prompt with hard anti-hallucination rules, the retrieved-data JSON
  (never raw SQL rows), and recent conversation history (client-supplied,
  capped at `max_history_turns`).
- **`response_formatter.py`** — appends a **deterministic** "Data Sources"
  footer built from the actual endpoints `tool_executor` called for this
  turn, never from what the LLM claims — a real anti-hallucination guardrail,
  not cosmetic citation.
- **`copilot_service.py`** — orchestrates one turn: detect intent → call
  exactly the tools that intent needs → assemble context → stream the LLM's
  answer → append the verified source footer. If the LLM itself is
  unreachable, it says so honestly rather than truncating silently or
  inventing an answer.

**No new database tables.** Conversation history is kept client-side (sent
with each request) and nothing about a turn is persisted server-side — every
answer is a live recomputation from already-persisted data (health scores,
predictions, orders), the same reasoning `recommendation_service.py` uses.

### 8.2 Example flow — "Which customers should I contact this week?"

`intent_router` matches this to `CONTACT_LIST` (a regex, not an LLM call) →
`copilot_service` calls `GET /recommendations/customers` via `tool_executor`
→ that JSON (already-ranked contact recommendations with reasons) becomes the
"Retrieved Data" in the prompt → the LLM phrases it as Business Insight /
Supporting Data / Recommended Action → `response_formatter` appends
`Data Sources: Recommendation Engine`.

### 8.3 UI — embedded in Analytics, not a separate page

A collapsible **Sales Copilot** panel sits at the bottom of the Analytics
page (`components/copilot/CopilotPanel.tsx`) — suggested-question chips, a
scrolling chat window with auto-scroll and a per-message copy button, a
typing-dots loading animation, and a clear-conversation control. Responses
stream token-by-token via `fetch` + `ReadableStream` (not axios, which isn't
a good fit for reading a streaming POST body in the browser).

---

## 9. Recommendation Engine

**Status: implemented (Milestone 9).** Rule-based, not ML/LLM-based — the
brief explicitly rules out an LLM here. `backend/app/recommendation_engine/`
combines already-computed Health Scores, Purchase Predictions, and live
order/college aggregates through configurable business rules to produce
ranked, explainable recommendations. Nothing here is persisted to a table:
every call recomputes live from data that's already persisted elsewhere
(health scores, predictions, orders), so a recommendation is always in sync
with the latest scoring run — the same reasoning `explainability_service.py`
uses to compose existing services rather than owning its own data.

- **Module layout** (mirrors `health_score/`'s separation of concerns):
  `config.py` (tunable thresholds — contact/risk/regional/sales cutoffs and
  the High/Medium/Low priority-score bands), `rules.py` (the business rules
  themselves — pure `signals -> Recommendation | None` functions registered
  in per-type lists; adding a rule means writing one function and appending
  one entry), `priority_engine.py` (pure 0-100 urgency scoring + banding, kept
  separate from rule *conditions* so "how urgent" can be retuned without
  touching "does this fire"), `recommendation_service.py` (the only module
  that touches Postgres — assembles signal objects from `HealthScoreService`,
  `predictions_service`, and `Order`/`College` queries, then calls `rules.py`).
- **Four recommendation types**, seven rules total:
  - **Customer** — `contact_high_probability`: any customer above a
    purchase-probability floor gets a "Contact {name} this week." The literal
    brief example (`IF Purchase Probability > 85% AND Health Score > 70 THEN
    Priority = High`) is applied exactly as a discrete rule
    (`priority_engine.band_for_contact`); everything else that clears the
    floor lands at "medium" rather than being all-or-nothing.
  - **Risk** — `low_health_followup` (health score < 40) and
    `dormant_customer` (no purchase in 180+ days) both fire independently (a
    customer can trigger both), each scored by recency + how far below 40 the
    health score is + revenue at stake.
  - **Regional** — `regional_revenue_decline` (down > 15% over a 90-day
    rolling window, mirroring `health_service._revenue_growth`'s definition
    but grouped by region) and `regional_growth_opportunity` (up > 20%);
    thin-sample regions (< 3 orders) are skipped so a single order swing
    can't manufacture a false alert.
  - **Sales** — `rising_demand_forecast` / `falling_demand_forecast`: the sum
    of every current prediction's `expected_revenue` (next-30-days forecast)
    compared against **last month's actual** revenue, not the current
    still-in-progress month (which would understate the baseline and
    exaggerate the swing early in a month).
- **Priority scoring**: every rule type gets a continuous 0-100 score (for
  ranking within and across types) via `priority_engine.score_*`, banded into
  High/Medium/Low. Health score is weighted more heavily than recency in the
  risk score specifically — a deeply critical health score (already
  "critical" by `health_score/config.py`'s own bands) must surface as at
  least medium priority even with only average recency, not get diluted by
  it.
- **API** — `GET /recommendations` (everything, ranked), `/recommendations/
  customers`, `/recommendations/regions`, `/recommendations/high-priority`,
  `/recommendations/risk`. No `/recommendations/sales` endpoint exists per se
  (not in Milestone 9's API list) — sales-type recommendations surface
  through the aggregate `/recommendations` endpoint instead.
- **Frontend** — a new **Recommendations** page (`pages/Recommendations.tsx`)
  with a KPI row, a cross-type "Suggested Actions" feed, and four sections
  (High Priority Customers, Critical Customers, Regional Opportunities,
  Revenue Alerts) built from a shared `RecommendationList` card component.
- **Cross-sell suggestions** (product-level, from the original draft) are
  **not** part of Milestone 9's brief and remain unbuilt — nothing here
  changes the products/orders domain.

---

## 10. Frontend Pages & Navigation

| Page | Purpose |
|---|---|
| Login | Auth |
| Dashboard | KPI summary, sales trend, region performance, top products |
| Colleges (list + detail) | Customer directory; detail view shows order history, health score trend, predictions |
| Products (list + detail) | Catalog; detail view shows sales trend, category performance |
| Orders | Order list/search, order detail with line items and payment status |
| Predictions | Ranked next-purchase forecasts, filterable by region/category |
| Customer Health | At-risk/dormant list, RFM breakdown, global feature-importance view |
| Insights | Feed of auto-generated business insights |
| Recommendations | Suggested actions + high-priority/critical customers, regional opportunities, revenue alerts *(Milestone 9, built as `/recommendations`)* |
| Analytics | Charts/KPIs/tables **plus an embedded, collapsible Sales Copilot panel** *(Milestone 10 — deliberately not a separate page; no standalone "AI Assistant" page exists)* |
| Data Import (admin) | CSV upload, job status/history |
| Admin | User management, model registry, retrain triggers |

Navigation: persistent left sidebar (MUI Drawer) with the above sections;
role-based visibility (Admin/Data Import hidden from sales_rep role).

---

## 11. Suggested Improvements (gaps in the original brief)

- ✅ **RBAC enforcement** — implemented Milestone 11: JWT auth, three roles
  (admin/sales_manager/sales_executive), every endpoint protected except
  login, two write endpoints role-restricted. See §15.
- **Background job runner (Celery + Redis)** — CSV import, batch scoring, and
  embedding ingestion are all long-running; running them inline in a FastAPI
  request handler would block and time out. Proposed as an addition to the
  stack. Still not built — `POST /ml/retrain` remains a synchronous
  subprocess call with a 600-second timeout.
- **Audit logging** — who triggered a retrain, who uploaded a document, who
  imported data — useful even in an internship/demo project for trust in the
  "explainable" story. Still not built (the access-log middleware added in
  Milestone 11 logs *that* a request happened, not a queryable audit trail
  of *who did what*).
- **Model monitoring** — track prediction accuracy/drift over time in
  `model_registry.metrics`, surfaced in the Admin page.
- **Copilot feedback loop** — thumbs up/down on Copilot answers. Would need a
  new (currently nonexistent) persistence layer, since the Copilot
  keeps no server-side chat history to attach feedback to.
- **Rate limiting on `/copilot/chat` and `/auth/login`** — free-tier LLM
  providers (Groq/OpenRouter) enforce their own rate limits, but this
  backend doesn't cap requests/session, requests/user/day, or login
  attempts itself yet — still open after Milestone 11.
- ✅ **Caching** — implemented Milestone 11, though as an in-process TTL
  cache (`app/core/cache.py`), not Redis — sufficient for a
  single-backend-replica deployment; Redis is the natural upgrade once
  there's more than one backend instance sharing state matters. See §15.
- **Testing** — pytest coverage exists for `health_score/`,
  `recommendation_engine/`, `copilot/`, `auth/`, and the caching/error-
  handling middleware (Milestone 11 added dedicated suites for the last
  three); the frontend now has a real test suite too (Vitest + React
  Testing Library, Milestone 11). Still missing: an evaluation set of
  question/expected-answer pairs for the Sales Copilot — accuracy isn't
  optional for a system marketed as "explainable", but a proper eval
  harness is a bigger investment than this milestone's scope.

---

## 12. Phased Development Roadmap

Each phase produces something runnable/demoable before moving to the next.

**Phase 0 — Scaffolding**
Repo structure, Docker Compose skeleton (postgres, backend, frontend
containers), env config, empty FastAPI app + empty React app talking to each other.

**Phase 1 — Data foundation**
Alembic migrations for all schema tables (§4); mock data generator producing
500 colleges / 100 products / 20k+ orders with the specified realism
(seasonality, dormancy, payment delays, discounts); load into Postgres.

**Phase 2 — Core CRUD + Auth** ✅ *(Auth half only — Milestone 11)*
Auth (JWT, roles) ✅ implemented Milestone 11 — see §15. Colleges/products/
orders CRUD APIs and the CSV import endpoint are still read-only/not built
(write-side CRUD remains explicitly out of scope — every milestone through
11 only ever *reads* the mock-seeded data).

**Phase 3 — Dashboards**
Dashboard/KPI APIs + frontend Dashboard, Colleges, Products, Orders pages
(no ML yet — pure aggregation).

**Phase 4 — ML pipeline v1** ✅ *(Milestones 5-7)*
Feature engineering, XGBoost next-purchase model, batch scoring job,
`predictions` populated. (Health score shipped as a weighted formula, not an
XGBoost model — see §6a.)

**Phase 5 — Explainability** ✅ *(Milestone 8)*
SHAP explainer fitting, `shap_explanation` persisted, Sales Opportunities +
Customer Detail frontend pages with feature-contribution views.

**Phase 6 — Recommendations** ✅ *(Milestone 9, partial)*
Rule-based customer/risk/regional/sales recommendation endpoints +
Recommendations frontend page. Scheduled insight generation / Insights
frontend page (the "Insights" half of this phase) is still not built.

**Phase 7 — Sales Copilot** ✅ *(Milestone 10 — supersedes the original "RAG
Assistant" plan)*
No document ingestion, no FAISS index, no LangChain agent, no Claude.
Deterministic intent routing (`app/copilot/intent_router.py`) + tool calls
into this backend's own REST API (`tool_executor.py`, in-process, never
direct SQL) + a free OpenAI-compatible LLM (Groq/OpenRouter/Ollama,
`llm_provider.py`) to phrase the grounded answer. Streamed, embedded as a
collapsible panel in the Analytics page — no separate chat page/session
storage.

**Phase 8 — Hardening & Deployment** ✅ *(Milestone 11, partial)*
RBAC enforcement pass ✅, caching ✅, tests ✅ (all three projects),
production Docker Compose profile ✅ (`docker-compose.prod.yml`, multi-stage
`Dockerfile`s), README/runbook ✅ (full `docs/` set). Rate limiting and a
background job runner are still not built — see §11.

We will build and validate one phase at a time; no phase starts until the
previous one is confirmed working.

---

## 13. Mock Data Generation Rules

To be implemented in Phase 1, but specified now so the schema supports it:

- **500 colleges**, ~60/40 government/private split, distributed across a
  fixed set of regions/states, with a mix of `active` and intentionally
  `dormant` accounts (no orders in the last 180+ days).
- **100 products** across multiple categories (e.g., glassware, reagents,
  analytical instruments, safety equipment, consumables), with realistic price
  bands per category.
- **20,000+ orders** over a 3-year window with:
  - seasonal peaks (e.g., academic-year start, grant-cycle months)
  - repeat-customer clustering (a subset of colleges order frequently and
    predictably; others sporadically)
  - dormancy (some colleges stop ordering partway through the window — this
    is the churn signal the health-score model learns from)
  - payment delays (a configurable % of orders have `payment_status=overdue`
    or a `payment_received_date` well past `payment_due_date`)
  - discounting patterns correlated with order size/institution type
  - government colleges skewing toward slower payment and bulk/annual orders;
    private colleges skewing toward smaller, more frequent orders

---

## 14. Open Decisions for Approval — resolved by implementation (Milestones 1-10)

This section is from the original pre-implementation draft; all four
questions have since been settled by what was actually built, not by a
separate approval step:

1. ~~Confirm **Celery + Redis** addition for background jobs~~ — deferred;
   everything so far (ML retraining, batch scoring, health-score recalc) runs
   synchronously and has been fast enough not to need it (see §11).
2. ~~Confirm **sentence-transformers** (local) for embeddings, with Claude
   reserved for reasoning/generation only~~ — moot: Milestone 10 uses no
   embeddings/vector store at all, and no Claude — see §8.
3. ~~Confirm the **constrained structured-query tool** approach for RAG over
   free-form NL-to-SQL~~ — the *principle* survived (the Sales Copilot never
   lets the LLM query anything freely), but the mechanism is simpler than
   planned: deterministic intent routing + calls into this backend's own
   REST API, not a LangChain agent choosing from a tool list.
4. ~~Confirm phase order in §12~~ — settled by each milestone's actual
   request order (ML → Explainability → Recommendations → Sales Copilot), see
   §12.

---

## 15. Enterprise Production Readiness (Milestone 11)

**Status: implemented.** The feature set was complete after Milestone 10;
this milestone added no new business features — it's entirely about taking
what exists and making it feel like software that could be deployed inside
a real company: authentication, consistent error handling, performance,
testing, documentation, and Docker hardening. It also served as a full
codebase review, which caught and fixed one real, previously-unnoticed
production bug (see below).

### 15.1 Authentication & RBAC

- `backend/app/auth/` — `security.py` (bcrypt password hashing + JWT encode/
  decode, zero I/O), `auth_service.py` (`authenticate_user`,
  `issue_token_for`), `dependencies.py` (`get_current_user`,
  `require_role(*roles)`).
- **Every endpoint requires authentication except `POST /auth/login` and
  `GET /health`.** Enforced once, at the router-group level
  (`app/api/v1/api.py` wraps every domain router in a `_protected_router`
  with `dependencies=[Depends(get_current_user)]`) — not sprinkled across
  every route function individually.
- **Two endpoints are additionally role-restricted** to `admin`/
  `sales_manager` (not `sales_executive`): `POST /ml/retrain` and `POST
  /customers/health` — both rewrite data across the whole business, not a
  read-only lookup.
- **Frontend:** `context/AuthContext.tsx` (token in `localStorage`,
  rehydrated + validated against `GET /auth/me` on load), `pages/Login.tsx`,
  `components/auth/ProtectedRoute.tsx` (wraps the entire protected route
  tree; supports an optional `allowedRoles` prop for role-gating a whole
  page, though no page currently needs more than "any logged-in user" — the
  two role-restricted actions are individual buttons, gated inline with a
  disabled state + explanatory tooltip, since the backend remains the real
  authority either way).
- **A real architectural consequence:** the Sales Copilot's `tool_executor`
  makes in-process calls into this same backend's API (see §8) — now that
  those calls require auth too, `copilot_service.answer()` forwards the
  *asking user's own* bearer token to every internal tool call, so the
  Copilot always acts with the caller's own permissions, never an elevated
  service account.

### 15.2 Standardized error handling & observability

- **Every error response, from any router, has the same shape:**
  `{"detail": ..., "error_code": ..., "request_id": ...}`
  (`app/core/exception_handlers.py`) — three handlers
  (`HTTPException`, `RequestValidationError`, generic `Exception`) replace
  the two ad hoc ones `main.py` had before. `detail` is kept as the
  top-level key (FastAPI's own convention, already used by every existing
  `raise HTTPException(..., detail=...)` call) so this is additive, not a
  breaking rename.
- **`app/core/middleware.py`** — a request-ID + access-log middleware.
  Every request gets a UUID (reusing one supplied by an upstream proxy, so
  traces stay joined across a load balancer), stamped onto the response's
  `X-Request-ID` header and into one structured log line per request
  (`METHOD path -> status (Xms) [request_id]`, log level following the
  status code).

### 15.3 Performance

- **`app/core/cache.py`** — a minimal in-process TTL cache (no Redis; see
  §11 for why that's the right call at this scale). Applied to every
  aggregation-heavy read path: `dashboard_service`, `analytics_service`,
  `products_service`, `HealthScoreService.compute_factors` (the genuinely
  expensive one — a full order-table scan per college, in Python), and the
  recommendation engine's per-college/per-region signal assembly. 20-30
  second TTL, invalidated immediately (`cache.clear_all()`) after a
  retrain or health recalculation.
- **Frontend code splitting** — every page is `React.lazy`-loaded
  (`routes/AppRoutes.tsx`); vendor libraries (React, MUI, Recharts, React
  Query) are split into their own cacheable chunks
  (`vite.config.ts`'s `manualChunks`). Verified via a real production
  build — see `docs/ARCHITECTURE.md`'s Performance & caching section for
  the resulting chunk sizes.

### 15.4 Testing

- **Backend** — 53 tests (up from 38 before this milestone): new
  `tests/test_auth.py` (login success/failure, `/me`, role restriction,
  inactive-user rejection), `tests/test_cache.py` (TTL behavior), a shared
  `tests/conftest.py` (`auth_headers`/`sales_manager_headers`/
  `sales_executive_headers` fixtures — real login against a real test user,
  not mocked auth).
- **Frontend** — a testing setup didn't exist before this milestone. Added
  Vitest + React Testing Library + jsdom (`vite.config.ts`'s `test` block,
  `src/test/setup.ts`). 27 tests: `utils/format.test.ts` (pure functions),
  `components/common/StatusChip.test.tsx` and
  `components/table/DataTable.test.tsx` (presentational components, every
  loading/empty/error/rows state), `hooks/useCopilotChat.test.ts` (mocked
  streaming API), `pages/Login.test.tsx` (a full authentication-flow page
  test, mocking `useAuth`).
- **ML** — unchanged (27 tests already existed from earlier milestones).

### 15.5 Docker & deployment

- **Both `Dockerfile`s are now multi-stage** with `dev` and `production`
  targets sharing one dependency-install layer. `dev` matches the previous
  behavior exactly (hot-reload, source volume-mounted). `production`:
  non-root user, no reload, `uvicorn --workers 4` (backend) / an `nginx`
  static-file stage with no Node.js at all (frontend) + `nginx.conf`
  (SPA-fallback routing, gzip, long-cache immutable hashed assets,
  `no-cache` on `index.html`, basic security headers). Both declare a
  `HEALTHCHECK`.
- **`docker-compose.yml`** now explicitly targets `dev` on both services
  (previously implicit — a bare `docker build` on a multi-stage Dockerfile
  defaults to the *last* stage, which would have silently broken local dev
  by building the production image instead the moment this became
  multi-stage).
- **New `docker-compose.prod.yml`** — the production stack: no source
  mounts, `POSTGRES_PASSWORD` required (compose refuses to start without
  it), `VITE_API_BASE_URL` passed as a frontend build ARG (Vite bakes it
  into the JS bundle at build time, not read at container-start), a
  read-only volume mount for `ml/artifacts` so the backend can serve SHAP
  plot PNGs without needing the `ml/` toolchain itself.
- **A real bug found and fixed by testing the production image directly**
  (not just building it): `PLOTS_DIR`'s relative-path derivation
  (`Path(__file__).resolve().parents[2]`) resolves differently inside a
  container than on a local checkout, and a standalone backend container
  crashed on startup trying to `mkdir` a path it didn't have permission to
  create. Fixed two ways: (1) `app/core/config.py` gained a `plots_dir`
  setting so this is explicitly configurable in containers (used by
  `docker-compose.prod.yml`), and (2) `main.py`'s directory-creation is now
  wrapped in a `try/except OSError` that logs a warning instead of
  crashing the whole app — serving SHAP plot images is a secondary
  feature, and a misconfiguration there shouldn't take down the API.

### 15.6 Dead code removed / bugs fixed

- **`app/ml/` and `app/rag/`** — two never-implemented placeholder packages
  from the original scaffolding (confirmed via grep: nothing imported
  them). Deleted.
- **`GET /settings/profile`** — a hardcoded stub that always returned
  `{"user": "demo_user", "role": "admin", ...}` regardless of who was
  actually logged in. Now that real auth exists, this was actively
  misleading, not just unfinished — removed; `Settings.tsx` now reads the
  real authenticated user from `AuthContext`.
- **`GET /predictions/feature-importance` — found broken during this
  milestone's review, not introduced by it.** Milestone 8 changed the
  shape of `global_feature_importance.json` (per-model breakdown) but this
  older Milestone-7 endpoint (and its schema, and the frontend's
  `useFeatureImportance` hook) was never updated to match — it had been
  silently 500ing (a Pydantic validation error on every call) since
  Milestone 8 shipped, and the Sales Opportunities page's "What's Driving
  Purchase Likelihood" chart had been broken that whole time without
  anyone noticing (it fails silently in the UI — a loading/error state,
  not a visible crash). Fixed by removing the dead endpoint/schema/service
  function entirely and switching the frontend to the correct,
  already-built `GET /explain/top-features` endpoint (built in Milestone 8
  for exactly this purpose, just never wired up to this chart). Verified
  via a live browser test showing real SHAP feature-importance data
  rendering correctly.

### 15.7 Accessibility

- Every icon-only `IconButton` across the app now has an `aria-label`
  (audited via grep for `<IconButton` without one) — the Sales Copilot
  panel's expand/collapse, copy, send, and clear buttons; the Customer/
  Product Detail back buttons; the Login page's show/hide-password toggle.
- Text inputs without a visible `<label>` (the global search box, the
  Copilot's question input) got an explicit `aria-label` via
  `slotProps.htmlInput`.
- React Router's v7 future flags (`v7_startTransition`,
  `v7_relativeSplatPath`) were opted into early, clearing a console warning
  that appeared on every route.

