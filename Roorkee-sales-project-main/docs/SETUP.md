# Setup Guide

Two ways to run SalesPilot AI locally: **Docker Compose** (fastest, fewest
moving parts) or **manual** (each of the four projects run natively — better
for active development, since you get instant hot-reload without a
container rebuild).

## Prerequisites

- Docker + Docker Compose (for the Docker path)
- Node.js 20+ and npm (for the manual frontend path)
- Python 3.12+ (for the manual backend/ml path)
- ~2 GB free disk space (Postgres data + two Python venvs + node_modules)

## Option A — Docker Compose (recommended for a first run)

```bash
git clone <repo-url>
cd sales_ai_internship_project
cp .env.example .env
docker compose up --build
```

This starts Postgres, the backend (hot-reload), and the frontend
(hot-reload) — but **does not seed data or train models**. Run these once
against the running stack:

```bash
# Seed mock colleges/products/orders
docker compose exec backend python -m app.db.seed

# Apply migrations (creates all tables, including users)
docker compose exec backend alembic upgrade head

# Seed the three demo user accounts
docker compose exec backend python -m app.db.seed_users
```

Then visit **http://localhost:5173** and log in with any demo account (see
`docs/ENVIRONMENT_VARIABLES.md` for the list — password `ChangeMe123!` for
all three).

The ML pipeline (`ml/`) is **not** part of the Docker Compose stack (it's a
one-shot batch job, not a long-running service) — see Option B below to run
it, or trigger it from inside the app via **Sales Opportunities → Retrain
Models** (requires an Admin or Sales Manager account) once `ml/`'s own venv
is provisioned per Option B step 4.

## Option B — Manual (native) setup

### 1. Postgres

Easiest via Docker even if you're running everything else natively:

```bash
docker compose up postgres -d
```

Or point `DATABASE_URL` in `.env` at any Postgres 14+ instance you already have.

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements-dev.txt

alembic upgrade head
python -m app.db.seed
python -m app.db.seed_users

uvicorn app.main:app --reload
```

Backend now running at **http://localhost:8000** (interactive API docs at
`/docs`).

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend now running at **http://localhost:5173**.

### 4. ML pipeline (optional — only needed to generate real predictions/SHAP explanations)

```bash
cd ml
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt

python run_pipeline.py          # feature engineering
python -m prediction.train      # trains + scores + generates SHAP plots
```

After this, **Sales Opportunities → Retrain Models** in the UI (or `POST
/api/v1/ml/retrain`) will work end-to-end, since it shells out to this same
`ml/.venv`.

### 5. Sales Copilot (optional — only needed for real LLM answers)

Get a free Groq API key at <https://console.groq.com/keys>, then add to
`.env`:

```
GROQ_API_KEY=gsk_...
```

Restart the backend. Without this, the Copilot still runs its full
grounding pipeline but reports it can't reach a language model — see
`docs/ENVIRONMENT_VARIABLES.md`.

## Verifying the setup

```bash
curl http://localhost:8000/health
# {"status":"ok","environment":"development"}

curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@salespilot.example.com&password=ChangeMe123!"
# {"access_token": "...", "role": "admin", ...}
```

Then open http://localhost:5173, log in, and click through Dashboard →
Customers → Analytics (the Sales Copilot panel is at the bottom) →
Recommendations.

## Running the test suites

```bash
# Backend
cd backend && pytest -q

# Frontend
cd frontend && npm test

# ML
cd ml && pytest -q
```

See `docs/DEVELOPER_GUIDE.md` for more on the testing conventions.

## Troubleshooting

- **`psycopg2.OperationalError: could not connect`** — Postgres isn't
  running, or `DATABASE_URL`'s host/port doesn't match. If running natively
  (not Docker) against the Dockerized Postgres, the port is `5433`, not
  `5432`.
- **Login works but every other page 401s** — the token likely expired
  (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 8h) or `JWT_SECRET_KEY` changed
  between backend restarts (any restart with a new secret invalidates every
  previously-issued token). Log in again.
- **Charts on the Dashboard/Analytics pages are empty** — you haven't run
  `python -m app.db.seed` yet.
- **Sales Opportunities / Explainability tabs show "not available yet"** —
  you haven't run the ML pipeline (`ml/run_pipeline.py` +
  `python -m prediction.train`) yet, or `POST /api/v1/ml/retrain`.
- **Sales Copilot always says it can't reach the language model** — no
  `GROQ_API_KEY`/`OPENROUTER_API_KEY` set and Ollama isn't running locally.
  This is expected without one of the three providers configured.
