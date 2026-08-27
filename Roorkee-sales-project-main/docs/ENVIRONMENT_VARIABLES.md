# Environment Variables

Two `.env` files, both gitignored, both with `.env.example` templates:

- **Root `.env`** — used by Docker Compose and the backend directly (when
  run outside Docker, `backend/app/core/config.py`'s `Settings` reads
  `.env` from the current working directory — run `uvicorn` from `backend/`
  with a `backend/.env`, or export the same variables in your shell).
- **`frontend/.env`** — used by Vite (`VITE_API_BASE_URL`).

Copy `.env.example` → `.env` at the repo root and adjust before running
anything for real.

## General

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | Free-form; surfaced in `GET /health` and startup logs. |
| `LOG_LEVEL` | `INFO` | Standard Python logging levels. |

## PostgreSQL

| Variable | Default | Notes |
|---|---|---|
| `POSTGRES_USER` | `salespilot` | |
| `POSTGRES_PASSWORD` | `salespilot_dev_password` | **Must** be overridden for any real deployment — `docker-compose.prod.yml` refuses to start without it set. |
| `POSTGRES_DB` | `salespilot` | |
| `POSTGRES_HOST` | `127.0.0.1` | `127.0.0.1`, not `localhost` — avoids an intermittently flaky IPv6/WSL2 relay path on Docker Desktop for Windows. |
| `POSTGRES_PORT` | `5433` | Non-default on the host to avoid clashing with a locally-installed Postgres on 5432. |
| `DATABASE_URL` | `postgresql+psycopg2://salespilot:salespilot_dev_password@127.0.0.1:5433/salespilot` | Used directly by the backend. Docker Compose overrides the host to `postgres` (the service name) automatically. |

## Backend

| Variable | Default | Notes |
|---|---|---|
| `API_V1_PREFIX` | `/api/v1` | |
| `PROJECT_NAME` | `SalesPilot AI` | Shown in `/docs` and startup logs. |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | JSON array. Add your production frontend origin here or the browser will block every request with a CORS error. |
| `PLOTS_DIR` | *(empty)* | Where SHAP plot PNGs are read from. Empty = derive from the repo layout automatically (local dev). **Set explicitly in containers** — `docker-compose.prod.yml` sets it to `/ml-artifacts/prediction/plots`, matching where it mounts the `ml/artifacts` volume. If misconfigured, the backend logs a warning and `/plots/*` 404s — it does not crash the app. |

## Authentication (Milestone 11)

| Variable | Default | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | `dev-only-insecure-secret-change-me` | **REQUIRED to change for any real deployment.** Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Anyone who has this value can forge a valid login token for any user. |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` (8 hours) | How long a login session lasts before the user must log in again. |

Demo accounts (seeded via `python -m app.db.seed_users`, password
`ChangeMe123!` for all three — **change or remove these before any real
deployment**):

| Role | Email |
|---|---|
| Admin | `admin@salespilot.example.com` |
| Sales Manager | `manager@salespilot.example.com` |
| Sales Executive | `executive@salespilot.example.com` |

## Sales Copilot LLM provider (Milestone 10)

Free OpenAI-compatible providers only — no Claude, no OpenAI's own hosted
API. Auto-selected in this order: Groq (if `GROQ_API_KEY` is set) →
OpenRouter (if `OPENROUTER_API_KEY` is set) → Ollama (local, no key needed,
final fallback). Set `COPILOT_LLM_PROVIDER` to force one explicitly.

| Variable | Default | Notes |
|---|---|---|
| `COPILOT_LLM_PROVIDER` | *(empty = auto-detect)* | `"groq"` \| `"openrouter"` \| `"ollama"` |
| `GROQ_API_KEY` | *(empty)* | Free key: <https://console.groq.com/keys> |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | |
| `OPENROUTER_API_KEY` | *(empty)* | Free key: <https://openrouter.ai/keys> |
| `OPENROUTER_MODEL` | `meta-llama/llama-3.3-70b-instruct:free` | |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Run `ollama serve` + `ollama pull llama3.2` first. |
| `OLLAMA_MODEL` | `llama3.2` | |

Without any provider configured, the Copilot still runs its full grounding
pipeline (intent detection, real API calls, context assembly) but reports
honestly that it can't reach a language model, rather than fabricating an
answer — see `app/copilot/copilot_service.py`.

## Frontend

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Baked into the JS bundle **at build time** (Vite convention) — for a containerized production build, pass it as a Docker build ARG (see `docker-compose.prod.yml`), not a runtime env var. |

## Never commit `.env`

Only `.env.example` files are tracked in git. If you accidentally commit a
real `.env`, rotate every secret in it immediately (`JWT_SECRET_KEY`,
`POSTGRES_PASSWORD`, any LLM API key) — treat it as compromised.
