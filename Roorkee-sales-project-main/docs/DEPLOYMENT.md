# Deployment Guide

This describes deploying the containerized production build
(`docker-compose.prod.yml`). It's written for a single-host deployment (one
VM/server running Docker) — the natural next step beyond that (managed
Postgres, a container orchestrator, autoscaling) is called out at the end
but not required to get a working production deployment.

## What's different between dev and production

| | `docker-compose.yml` (dev) | `docker-compose.prod.yml` (production) |
|---|---|---|
| Backend | `uvicorn --reload`, source volume-mounted | `uvicorn --workers 4`, source baked into the image |
| Frontend | Vite dev server (HMR) | Static build served by nginx (no Node.js in the final image) |
| Backend port exposed | `8000` | `8000` (put a reverse proxy / TLS terminator in front for real internet exposure) |
| Frontend port exposed | `5173` | `80` |
| Postgres port exposed to host | `5433` | *(not exposed — only reachable from the backend container)* |
| `POSTGRES_PASSWORD` | has a default | **required** — compose refuses to start without it |

Both Dockerfiles are multi-stage with named targets (`dev` / `production`),
so there's exactly one place package installation happens per project — the
two targets only differ in the final run command and whether source is
copied in vs. mounted.

## Prerequisites

- A host with Docker + Docker Compose installed
- A real Postgres password and a real `JWT_SECRET_KEY` (see
  `docs/ENVIRONMENT_VARIABLES.md`)
- (Optional but recommended) A free Groq API key for the Sales Copilot
- (Recommended) A reverse proxy (nginx, Caddy, Traefik) in front of ports 80
  and 8000 to terminate TLS — this repo doesn't set up HTTPS itself

## Steps

1. **Provision the host and clone the repo.**

   ```bash
   git clone <repo-url>
   cd sales_ai_internship_project
   ```

2. **Configure `.env`.** Copy `.env.example` → `.env` and set, at minimum:
   - `POSTGRES_PASSWORD` (a real, unique password)
   - `JWT_SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`)
   - `BACKEND_CORS_ORIGINS` — include your real frontend origin(s), e.g.
     `["https://salespilot.example.com"]`
   - `VITE_API_BASE_URL` — the backend's real public URL, e.g.
     `https://api.salespilot.example.com/api/v1` (this gets baked into the
     frontend bundle at build time — see below)
   - `GROQ_API_KEY` (or another provider) if you want the Sales Copilot to
     give real answers

3. **Build and start the stack.**

   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env up -d --build
   ```

   `VITE_API_BASE_URL` is passed through as a build ARG automatically (see
   the `frontend` service's `build.args` in `docker-compose.prod.yml`) — if
   you change it, you must rebuild the frontend image (`--build`), not just
   restart the container, since Vite inlines it into the JS bundle rather
   than reading it at runtime.

4. **Run migrations and seed the demo accounts** (one-time, or after a
   schema change):

   ```bash
   docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
   docker compose -f docker-compose.prod.yml exec backend python -m app.db.seed_users
   ```

   Seed mock sales data too if this is a demo deployment (skip for a real
   deployment with real data):

   ```bash
   docker compose -f docker-compose.prod.yml exec backend python -m app.db.seed
   ```

5. **Verify.**

   ```bash
   curl http://<host>:8000/health
   curl http://<host>/          # nginx serving the frontend
   ```

6. **Put a reverse proxy in front** (not included) to terminate TLS and
   route `https://your-domain/` → frontend:80 and
   `https://your-domain/api/` → backend:8000. Update
   `BACKEND_CORS_ORIGINS` and rebuild the frontend with the final
   `VITE_API_BASE_URL` once the real domain is known.

## Running the ML pipeline against production data

The `ml/` project is not part of either Docker Compose file (it's a
one-shot batch job with heavy dependencies — pandas/xgboost/shap — that
would bloat the backend image if merged in). Two options:

- **Run it on the host directly**, pointed at the production `DATABASE_URL`
  (see `docs/SETUP.md` Option B step 4), then restart the backend
  container so it picks up the new model version — or just trigger
  `POST /api/v1/ml/retrain` from an Admin account once `ml/.venv` is
  provisioned and reachable from the backend container's `ML_PYTHON` path
  (see `app/api/v1/routers/ml_admin.py`; the current implementation shells
  out via a relative path assuming `ml/` and `backend/` are sibling folders
  on the *same filesystem* — for a fully-containerized ML pipeline, that
  router would need to change to call a separate ML-serving container
  instead. Not implemented here — see Future Improvements below).
- **Run it in a separate, temporary container** (build `ml/` with its own
  Dockerfile if you add one — none exists today) that shares the same
  Postgres and writes to a shared `ml/artifacts` volume.

## Health checks & monitoring

Both `Dockerfile`s declare a `HEALTHCHECK` (backend polls `/health`;
frontend polls `/`), so `docker ps` and any orchestrator that respects
Docker healthchecks will correctly report container health. Structured
request logs (`app.request` logger, one line per HTTP request with a
request ID, method, path, status, and duration) are written to stdout —
pipe them into whatever log aggregation you use (they're not written to a
file inside the container, by design, so container restarts don't lose
history and log rotation is someone else's problem).

## Rolling back

Every trained model version is kept (`ml/prediction/train.py` never deletes
old artifact directories), and `model_registry.is_active` tracks which one
is live — reverting to a previous model is a database update, not a
redeploy. Reverting *code* is a normal `git revert` + rebuild + redeploy.

## Future improvements for a larger-scale deployment

Not implemented in this project (see `PROJECT_SPEC.md §11` for the full
list) but worth knowing about before scaling beyond a single host:

- **Managed Postgres** (RDS, Cloud SQL, etc.) instead of the Postgres
  container, with automated backups.
- **A background job queue** (Celery + Redis) for retraining instead of a
  synchronous subprocess call with a 600-second timeout.
- **Redis-backed caching** instead of the current in-process TTL cache,
  once the backend runs as more than one replica (an in-process cache
  doesn't share state across replicas).
- **Rate limiting** on `/api/v1/copilot/chat` and `/api/v1/auth/login`.
- **A dedicated `ml/` container/service** so retraining doesn't depend on a
  shared filesystem path between the backend and `ml/` processes.
