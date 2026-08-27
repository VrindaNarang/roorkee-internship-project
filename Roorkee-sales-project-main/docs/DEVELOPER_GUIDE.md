# Developer Guide

For someone about to make a change to this codebase. See `docs/SETUP.md`
first if the app isn't running yet, and `docs/ARCHITECTURE.md` for the
system-level picture.

## Conventions to follow

### Backend

- **Routers are thin.** A route function parses/validates the request,
  calls exactly one service function, and returns its result. Business
  logic lives in `services/` or one of the three domain-engine packages —
  never in a router.
- **Domain engines follow a fixed internal shape.** `health_score/`,
  `recommendation_engine/`, and `copilot/` each have: a `config.py` (tunable
  thresholds, no logic), pure computation modules with zero I/O (trivially
  unit-testable), and exactly one service module that's the only thing
  allowed to touch the database or an external API. Follow this shape for
  any new engine rather than inventing a new pattern.
- **Errors are `HTTPException`, not bare exceptions.** Raise
  `HTTPException(status_code=..., detail="...")` — the three handlers in
  `app/core/exception_handlers.py` convert it into the standard envelope
  automatically. Don't hand-build error JSON in a route.
- **New protected endpoints need nothing extra.** Every router mounted
  under `_protected_router` in `app/api/v1/api.py` already requires
  authentication. Only add `dependencies=[Depends(require_role(...))]` if
  the specific endpoint needs *more* than "any logged-in user" (see
  `ml_admin.py`/`customers.py`'s `/health` POST for examples).
- **Cache carefully.** `app/core/cache.py`'s `@ttl_cache(seconds)` drops the
  first positional argument (always `db` or `self`) from the cache key —
  only use it on functions where that's true. Call `cache.clear_all()` after
  any write that should be visible immediately (see `ml_admin.py`,
  `customers.py`).
- **Migrations:** `alembic revision --autogenerate -m "..."` after changing
  a model in `app/models/`, then read the generated file before running
  `alembic upgrade head` — autogenerate is a good first draft, not
  infallible (it won't detect every kind of change, e.g. some check
  constraints).

### Frontend

- **One page, one file, in `pages/`.** Add the route to
  `routes/AppRoutes.tsx` as a `React.lazy` import (route-level code
  splitting is the default, not an opt-in).
- **Data fetching goes through React Query hooks**, one file per domain in
  `hooks/`, wrapping a typed function in `api/`. Never call `apiClient`
  directly from a page component.
- **Reuse the shared state components** — `DataTable` (loading/empty/error/
  rows), `ChartCard` (same, for a chart), `KpiCard`, `StatusChip`,
  `ErrorState`, `EmptyState`. A new page needing a loading spinner or empty
  state almost certainly shouldn't hand-roll one.
- **Auth-aware UI:** `useAuth()` (from `context/AuthContext`) gives
  `{ user, status, login, logout }`. To gate a whole route by role, pass
  `allowedRoles` to `<ProtectedRoute>`; to gate a single control (a button,
  not a page), check `user.role` inline and disable/hide with an explanatory
  `Tooltip` (see `SalesOpportunities.tsx`'s "Retrain Models" button for the
  pattern) — the backend is still the real authority, this is just UX.
- **Accessibility:** every icon-only `IconButton` needs an `aria-label`.
  Every text input without a visible `<label>` needs one via
  `slotProps.htmlInput['aria-label']`.

## Running tests

```bash
# Backend — pytest against the real dev Postgres
cd backend && pytest -q
# Just one file / one test:
pytest tests/test_auth.py -q
pytest tests/test_auth.py::test_login_fails_with_wrong_password -q

# Frontend — Vitest + Testing Library, jsdom environment
cd frontend && npm test
# Watch mode while developing:
npm run test:watch
# Coverage report:
npm run test:coverage

# ML — pytest, pure feature-engineering/explainability logic, no DB needed
cd ml && pytest -q
```

**Test conventions:**
- Backend tests that need an authenticated request use the `auth_headers`
  fixture (`tests/conftest.py`) — it creates (idempotently) a real test user
  and logs in for real, rather than mocking auth away. Never mock/stub the
  actual database in backend tests; hit the real dev Postgres (matches this
  project's established convention — see `tests/test_health.py`).
- Frontend component/hook tests mock the *API layer* (`vi.mock('../api/...')`),
  not React Query itself — render the real hook, assert on its output.
- Don't write a test that runs the real ML retrain subprocess (~30-60s,
  shells out to a separate Python environment) — monkeypatch
  `subprocess.run` if you need to test the role-check around
  `POST /ml/retrain` (see `tests/test_auth.py`'s
  `test_retrain_endpoint_allows_admin_and_sales_manager` for the pattern).

## Linting & type-checking

```bash
cd backend && python -m py_compile app/**/*.py   # or just run pytest — import errors surface immediately
cd frontend && npm run lint && npx tsc --noEmit -p tsconfig.json
```

Frontend CI-equivalent before pushing: `npx tsc --noEmit`, `npm run lint`,
`npm test`, `npm run build` (the build step catches anything the other
three miss, e.g. a dynamic import that doesn't resolve).

## Database access patterns

- Read services return **plain dicts or dataclasses**, not ORM objects
  directly, when the shape doesn't map 1:1 onto a table (e.g.
  `HealthScoreService.list_latest()` joins/derives a trend field) — let the
  router's `response_model` (a Pydantic schema) do the final coercion.
  Endpoints that return one row unmodified (e.g. `GET /auth/me`) can return
  the ORM object directly if the schema has `model_config =
  ConfigDict(from_attributes=True)`.
- Prefer a single query with `func.sum`/`func.count`/joins over N+1 loops.
  If you write a loop that issues a query per iteration, there's almost
  always a `group_by` that does it in one round trip — see
  `services/products_service.py`/`dashboard_service.py` for the pattern.

## Adding a new LLM provider to the Sales Copilot

`app/copilot/llm_provider.py`'s `ProviderSpec` is `(name, base_url, api_key,
model)` — any OpenAI-compatible chat-completions endpoint works with zero
new code. Add a new `CopilotSettings` field pair (`<provider>_api_key`,
`<provider>_model`) in `app/copilot/config.py`, add it to `_provider_specs()`
and the auto-detect order in `_select_provider_spec()`, done.

## Common gotchas

- **Vite env vars are build-time, not runtime.** Changing
  `VITE_API_BASE_URL` in a running container's environment does nothing —
  the value is already baked into the built JS. Rebuild the image.
- **A fresh `JWT_SECRET_KEY` invalidates every existing session.** Expected
  after a backend restart with a changed secret — not a bug.
- **The Sales Copilot's internal tool calls need the caller's own JWT.**
  `tool_executor.call_api(..., auth_header=...)` forwards it — if you add a
  new intent/tool call in `copilot_service.py`, don't forget to pass
  `auth_header` through, or that call will 401 silently (caught, surfaced
  to the LLM as a tool-call error, not a crash — but still wrong).
