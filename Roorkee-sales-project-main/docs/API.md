# API Documentation

The full, always-up-to-date, interactive API reference is generated
automatically by FastAPI from the actual route definitions and Pydantic
schemas — it can never drift out of sync with the real API the way a
hand-written doc can. **This file is a map, not a duplicate.**

- **Swagger UI:** `http://localhost:8000/docs` — browse every endpoint,
  see request/response schemas, and call endpoints directly from the
  browser (click "Authorize" and log in with a demo account's
  email/password to get a bearer token applied to every subsequent
  request).
- **ReDoc:** `http://localhost:8000/redoc` — the same spec, read-only,
  better for a long linear read-through.
- **Raw OpenAPI JSON:** `http://localhost:8000/openapi.json`.

## Authentication

Every endpoint except `POST /api/v1/auth/login` and `GET /health` requires
`Authorization: Bearer <token>`.

```
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
username=admin@salespilot.example.com&password=ChangeMe123!

→ { "access_token": "...", "token_type": "bearer", "role": "admin", "full_name": "Admin User" }
```

```
GET /api/v1/auth/me
Authorization: Bearer <token>

→ { "id": 1, "email": "...", "full_name": "...", "role": "admin", "is_active": true, "created_at": "..." }
```

Two endpoints require `admin` or `sales_manager` specifically (not
`sales_executive`) — everything else just needs any authenticated user:

- `POST /api/v1/ml/retrain`
- `POST /api/v1/customers/health`

## Endpoint groups

| Prefix | Purpose | Milestone |
|---|---|---|
| `/auth` | Login, current-user profile | 11 |
| `/dashboard` | Top-level KPIs, sales trend, top customers/products, recent orders | 4 |
| `/customers` | Customer directory, detail, orders, health scores | 4, 6 |
| `/products` | Product catalog, detail, sales trend | 4 |
| `/analytics` | Region performance, customer-composition insights | 4 |
| `/predictions` | Purchase-probability + expected-order-value forecasts per customer | 7 |
| `/explain` | SHAP explanations (per-customer and global feature importance) | 8 |
| `/recommendations` | Rule-based customer/risk/regional/sales recommendations | 9 |
| `/copilot` | Sales Copilot chat (streamed) | 10 |
| `/ml` | Trigger model retraining | 7 |

## Response shape

Every successful response is the Pydantic `response_model` declared on the
route — see Swagger UI for the exact schema per endpoint. Every **error**
response (any 4xx/5xx) has this consistent shape regardless of which router
raised it:

```json
{
  "detail": "Customer not found",
  "error_code": "NOT_FOUND",
  "request_id": "5077be59-5bf3-4cbc-8e58-f0aa38dc5f44"
}
```

`error_code` is a short machine-readable string (`UNAUTHORIZED`,
`FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR`, `INTERNAL_ERROR`, etc. — see
`app/core/exception_handlers.py` for the full status-code → code mapping).
`request_id` matches the `X-Request-ID` response header and the backend's
access-log line for that request — quote it when reporting a bug.

## The Sales Copilot endpoint is different

`POST /api/v1/copilot/chat` doesn't return a single JSON object — it streams
the answer as plain text (`Content-Type: text/plain`), chunk by chunk, as
the LLM generates it. See `frontend/src/api/copilot.ts` for a working
`fetch` + `ReadableStream` client, or:

```bash
curl -N -X POST http://localhost:8000/api/v1/copilot/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "Which customers should I contact this week?", "history": []}'
```

## Pagination

List endpoints that can return many rows (`GET /customers`, `GET
/products`) take `page`/`page_size` query params and return
`{"items": [...], "meta": {"total", "page", "page_size", "total_pages"}}`.
Endpoints that are inherently bounded (e.g. "top 10 opportunities") take a
plain `limit` param instead and return a bare array.
