# PROJECT_SUMMARY.md

**SalesPilot AI** — an Explainable-AI-powered Sales Intelligence CRM,
built across 11 milestones as a solo internship/portfolio project. This
document is the single-page summary for a resume, a GitHub profile, a
hackathon judge, or an internship interview — everything else in this repo
(`PROJECT_SPEC.md`, `docs/`) is the detailed backing material.

---

## 1. Complete Architecture

Four independently runnable projects, each with one clear job:

```
┌────────────────────┐  HTTPS   ┌──────────────────────────────────────────┐
│   React Frontend    │ ───────► │              FastAPI Backend              │
│  (MUI + Recharts)   │ ◄─────── │  REST API · JWT Auth · domain services    │
└────────────────────┘          │  Sales Copilot (intent routing + LLM)     │
                                 └───────┬────────────────────────────────┘
                                         ▼
                             ┌───────────────────────┐        ┌──────────────────────────────┐
                             │      PostgreSQL         │ ◄──── │   Offline ML Pipeline (ml/)    │
                             │  transactional store   │ writes│  features → XGBoost → SHAP     │
                             └───────────────────────┘        └──────────────────────────────┘
```

- **`frontend/`** — React 18 + TypeScript SPA. Route-level code splitting,
  a React Query data layer, JWT auth with role-aware UI, and a consistent
  loading/empty/error-state vocabulary reused across every page.
- **`backend/`** — FastAPI + SQLAlchemy 2 + Pydantic v2. Thin routers, real
  business logic in `services/` and three purpose-built rule engines
  (health score, recommendations, Sales Copilot), one standardized error
  envelope, JWT auth enforced once at the router-group level, an
  in-process TTL cache on every expensive read.
- **`ml/`** — an isolated Python project (own venv: pandas, scikit-learn,
  XGBoost, SHAP, matplotlib) that engineers features, trains two models,
  fits SHAP explainers, and writes versioned artifacts + plot images. The
  backend never trains anything — it only loads what this pipeline
  produces.
- **PostgreSQL** — the single source of truth. Every number shown anywhere
  in the UI traces back to a real row in a real table (or a live SHAP/
  rule computation over those rows) — nothing is hardcoded or mocked past
  the initial data-generation step.

**Design principle threaded through every layer:** the backend is the only
integration point (frontend never touches Postgres or an LLM directly), ML
training is offline while inference is online, and every "smart" feature
(health score, recommendations, Copilot) is a readable, explainable engine
— never a model whose reasoning can't be inspected. Full detail:
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 2. Features

| Feature | What it does |
|---|---|
| **Analytics Dashboard** | Live KPIs, revenue trend, category distribution, regional performance, top customers/products — computed from real orders |
| **Customer Directory & Detail** | Searchable/filterable/paginated customer list; detail page with full order history, health score, purchase prediction |
| **Customer Health Score** | Transparent, weighted 0-100 score across 10 factors (recency, payment reliability, growth trend, etc.) — not a black-box model |
| **Purchase Propensity Prediction** | Two XGBoost models rank every customer by purchase probability and expected order value; versioned, never-deleted model artifacts |
| **Explainable AI (SHAP)** | Every prediction and health score comes with plain-English reasons, factor breakdowns, and waterfall/force/summary plots |
| **Business Recommendation Engine** | Rule-based "contact this customer," "follow up on this risk," "respond to this regional swing" — ranked by priority, no LLM involved |
| **Embedded AI Sales Copilot** | Ask a business question in plain English, right inside Analytics — grounded entirely in this backend's own API, phrased by a free LLM |
| **Authentication & RBAC** | JWT login, three roles (Admin/Sales Manager/Sales Executive), sensitive actions role-restricted |
| **Dark mode, responsive layout, accessible UI** | Persisted theme toggle, mobile-friendly sidebar, ARIA labels on every icon control |

---

## 3. ML Pipeline

**`ml/` — a standalone, offline pipeline, isolated from the live API.**

1. **Feature engineering** (`ml/preprocessing/`, `ml/features/`) — loads
   directly from Postgres, cleans/validates/deduplicates, and engineers
   RFM (recency/frequency/monetary), tenure, seasonality, and trend
   features per customer.
2. **Training** (`ml/prediction/train.py`) — two XGBoost models:
   - a **classifier** for "will this college purchase in the next 30 days"
   - a **regressor** for "how much, if they do" (trained only on customers
     who did purchase — a standard two-part/hurdle formulation)
   Both trained with a proper train/val/test split and cross-validated
   hyperparameter search. Every trained version is kept on disk
   (`ml/artifacts/prediction/<version>/`) — nothing is ever overwritten,
   so reverting to a previous model is a `model_registry` update, not a
   retrain.
3. **Batch scoring** (`ml/prediction/predict.py`) — runs both models over
   every customer, computes SHAP explanations for each prediction, and
   writes everything (predictions, SHAP JSON, plot PNGs) back to Postgres
   and disk in one pass (~60 seconds for the full dataset).
4. **Trigger** — `POST /api/v1/ml/retrain` (Admin/Sales Manager only)
   shells out to this pipeline in the `ml/` project's own Python
   environment, so the backend's own dependency footprint never needs
   pandas/XGBoost/SHAP.

---

## 4. Explainable AI Pipeline

**Why SHAP, and how it's made readable for a non-technical sales manager.**

- **`shap.TreeExplainer`**, cached per model (`ml/explainability/
  explainer.py`) so it's fit once, not once per prediction.
- **Dummy-column aggregation** (`ml/explainability/utils.py`) — SHAP
  values are additive by construction, so a one-hot-encoded categorical
  feature's dummy columns can be summed back to the original feature
  exactly (not approximately) — a sales manager sees `state`, never
  `state_Maharashtra` + `state_Gujarat` + ...
- **Business-friendly phrasing** — a per-feature phrase-template dictionary
  turns a signed SHAP value into a sentence like *"Payment delayed by 18
  days"* instead of `feature_importance = 0.23`.
- **Local vs. global explainability:**
  - *Local* (`GET /explain/customer/{id}`) — why **this** customer's score/
    prediction is what it is: top positive/negative factors, reason
    sentences, waterfall + force plots.
  - *Global* (`GET /explain/global`, `/explain/top-features`) — what's
    driving predictions **across the whole customer base** right now,
    aggregated from the full SHAP matrix (not from truncated per-row top-5
    lists, which would undercount features that weren't in everyone's top
    5).
- **The Customer Health Score gets the same treatment without SHAP at
  all** — it's a transparent weighted formula, not an ML model, so its
  `component_breakdown` (raw value, normalized score, weight, contribution
  per factor) is already an *exact* Shapley-style decomposition by
  construction. `backend/app/health_score/explanations.py` phrases it with
  the same "+ / -" sentence style, so all three "models" (health score,
  purchase probability, expected order value) read consistently in the UI.

---

## 5. AI Sales Copilot Workflow

**A business-question chat embedded in the Analytics page — no RAG, no
vector database, no document ingestion, grounded entirely in this
backend's own REST API.**

```
question ──► intent_router (regex, no LLM) ──► tool_executor
                                                  │ (in-process ASGI call into
                                                  │  this same API, forwarding
                                                  │  the asking user's own JWT)
                                                  ▼
                                          backend REST endpoints
                                          (analytics/predictions/
                                           health/explain/recommendations)
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

- **Deterministic intent detection**, not LLM function-calling — free-tier
  models support tool-calling inconsistently, so a regex router
  (`intent_router.py`) maps each question to one of 9 intents, guaranteeing
  the same question always triggers the same backend calls.
- **The LLM never sees the database.** `tool_executor.py` only knows REST
  paths — it gets back exactly the JSON a human calling the API would see,
  through the exact same routing/validation every other client uses.
- **A real anti-hallucination guardrail:** the "Data Sources" footer is
  appended by code, from the actual endpoints called — never generated by
  the LLM, which is explicitly instructed not to write one itself.
- **Honest failure mode:** if the LLM itself is unreachable (no provider
  configured), the Copilot says so plainly instead of fabricating an
  answer — the retrieved data is still real even when the phrasing step
  fails.
- **Free by design:** any OpenAI-compatible chat-completions API works
  (Groq, OpenRouter, Ollama) — no Claude, no OpenAI's own hosted API.

---

## 6. Folder Structure

```
sales_ai_internship_project/
├── backend/            # FastAPI service
│   └── app/
│       ├── auth/                     # JWT auth
│       ├── core/                     # config, middleware, exception handlers, cache
│       ├── health_score/             # weighted health-score engine
│       ├── recommendation_engine/    # rule-based recommendations
│       ├── copilot/                  # Sales Copilot
│       ├── services/, models/, schemas/, api/v1/routers/
├── frontend/           # React + Vite SPA
│   └── src/
│       ├── pages/, components/, context/, api/, hooks/
├── ml/                  # offline ML pipeline (own venv)
│   ├── preprocessing/, features/, prediction/, explainability/
├── docs/                # architecture, deployment, setup, API, developer guides
├── PROJECT_SPEC.md       # full design spec — source of truth
└── PROJECT_SUMMARY.md    # this file
```

Full breakdown of every subfolder: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md).

---

## 7. Technologies Used

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, MUI v6, Recharts, React Query, React Router, Axios |
| Backend | FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, PyJWT, bcrypt |
| ML / Explainability | pandas, scikit-learn, XGBoost, SHAP, matplotlib |
| Database | PostgreSQL 16 |
| AI Copilot | Groq / OpenRouter / Ollama (OpenAI-compatible chat API), `openai` Python SDK as a generic client |
| Testing | pytest (backend + ml), Vitest + React Testing Library (frontend) — 107 tests total |
| Infra | Docker, Docker Compose (multi-stage `dev`/`production` images), nginx |

---

## 8. Future Improvements

Deliberately out of scope so far (see `PROJECT_SPEC.md §11` for the full
reasoning behind each):

- **Write-side CRUD** and CSV import — every milestone through 11 only
  ever *reads* the mock-seeded data.
- **A background job queue** (Celery + Redis) — model retraining is
  currently a synchronous subprocess call with a 600-second timeout.
- **Redis-backed caching** — the current in-process TTL cache is correct
  and sufficient for a single backend replica, but doesn't share state
  once there's more than one.
- **Rate limiting** on `/copilot/chat` and `/auth/login`.
- **A scheduled insights feed** and product-level cross-sell suggestions.
- **A Copilot evaluation harness** — a real question/expected-answer test
  set, since "accuracy" isn't optional for a system marketed as
  explainable.
- **A dedicated `ml/` container/service**, decoupling retraining from a
  shared-filesystem assumption between the backend and `ml/` processes.

---

## 9. Business Impact

Built for a laboratory equipment company selling to colleges (government
and private) — the problem this solves:

- **"Who should I call today?"** — instead of a sales rep guessing or
  working a stale spreadsheet, the Recommendations page ranks every
  customer by a blended purchase-probability + health-score + revenue
  signal, refreshed continuously.
- **"Why is this customer at risk?"** — the health score and its SHAP-
  style breakdown turn a single 0-100 number into an actionable diagnosis
  ("payment delayed 18 days," "no purchase in 45 days") a rep can act on
  today, not just a red flag to worry about.
- **"Is this prediction trustworthy?"** — every ML output ships with its
  own explanation, which is what makes a purchase-probability score
  something a sales manager can defend to their own leadership, not a
  black box they have to take on faith.
- **"I don't have time to build a dashboard query"** — the Sales Copilot
  answers "why did sales decrease this month?" in the time it takes to
  type the question, grounded in the same data the dashboards show, not a
  hallucinated guess.
- **Trust by construction, not by disclaimer** — the health score is a
  transparent formula (not an ML model) specifically so its reasoning
  never needs to be taken on faith; the recommendation engine is
  rule-based (not an LLM) for the same reason; the Copilot cites its
  actual sources instead of claiming them.

---

## 10. Resume Description

> **SalesPilot AI — Explainable-AI Sales Intelligence CRM** *(solo
> project, 11 milestones)*
> Built a full-stack sales CRM (React/TypeScript + FastAPI/PostgreSQL) with
> two XGBoost models for purchase-propensity prediction, SHAP-based
> explainability surfaced as plain-English reasoning (not raw feature
> importances), a transparent rule-based recommendation engine, and an
> embedded AI Sales Copilot that answers natural-language business
> questions by calling the app's own REST API — never a direct database
> or vector-store query — and grounding a free LLM's response in that
> retrieved data. Added JWT authentication with role-based access control,
> a standardized error-handling/observability layer, an in-process caching
> layer, a from-scratch frontend test suite (Vitest + React Testing
> Library), and multi-stage production Docker builds. 107 automated tests
> across three independent projects (backend, frontend, ML pipeline).

**Shorter version (one line):**

> Built an explainable-AI sales CRM (React/FastAPI/PostgreSQL/XGBoost/SHAP)
> with a rule-based recommendation engine and an LLM-grounded Sales
> Copilot, hardened with JWT auth/RBAC, caching, and a 107-test suite
> across three independent projects.

---

## 11. Interview Talking Points

**"Walk me through the architecture."**
Four independent projects (frontend, backend, ML pipeline, docs), each
with a single job. The backend is the only integration point — the
frontend never touches Postgres directly, and the ML pipeline never runs
inside a request handler (training is offline; the backend only loads
versioned artifacts). I can point to `docs/ARCHITECTURE.md` for the full
request lifecycle.

**"Why did you choose SHAP over just showing feature importances?"**
Global feature importance tells you what matters on average across every
customer; it doesn't tell you why *this specific* customer got *this
specific* score. SHAP decomposes one prediction into per-feature
contributions that sum exactly to the difference from the baseline — that
additivity property is also what let me aggregate one-hot dummy columns
back to a readable original feature name without approximation.

**"Why is the health score not an ML model?"**
Because a rule-based, weighted formula is *more* explainable than any ML
model could be for this use case — every score comes with an exact
per-factor breakdown by construction, no explainer needed. I made the same
call for the recommendation engine: readable IF/THEN rules, not a model,
because a sales manager needs to trust *why* a recommendation fired, and a
rule they can read beats a model they have to take on faith.

**"How does the Sales Copilot avoid hallucinating business numbers?"**
Three layers: (1) it can only call this backend's own REST API — never SQL
directly, so it can't invent a query that returns something wrong; (2)
it's told explicitly to answer only from the retrieved JSON and to say so
plainly if the data it needs is missing; (3) the "Data Sources" footer is
generated by code from the *actual* endpoints called that turn, never by
the LLM itself, which is explicitly told not to write its own sources
section. That third one is the part I'm proudest of — it's a structural
guarantee, not a prompt-engineering hope.

**"What was the hardest bug you found?"**
Not something I introduced — something a systematic Milestone 11 review
caught: `GET /predictions/feature-importance` had been silently 500ing
since an earlier milestone changed the shape of the file it read, and the
Sales Opportunities page's feature-importance chart had been broken that
whole time without anyone noticing, because it failed into an empty/error
state rather than a visible crash. Fixed by removing the dead endpoint and
switching to the correct one that already existed. That's the kind of bug
that specifically motivated doing a real "production readiness" pass
instead of just shipping features and calling it done.

**"What would you do differently / what's next?"**
Move retraining off a synchronous subprocess call onto a proper job queue,
and swap the in-process cache for Redis once there's more than one backend
replica — both are the natural next step once this needs to scale past a
single host, and I designed the caching layer so that swap is a one-file
change, not a rewrite.
