"""Executes Copilot "tools" — thin wrappers that call this backend's OWN REST
API over an in-process ASGI transport, never the database directly. This
guarantees every number the LLM sees is exactly what a human calling the API
would see: the same routing, dependency injection, and Pydantic
serialization Milestones 4-9 already built and tested — no separate code
path that could quietly drift from what the real API returns.

`httpx.ASGITransport` drives the FastAPI app in-process (no real TCP round
trip), which is why this needs no network access and works identically
whether or not `uvicorn` is actually listening on a port.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        # Imported lazily: `app.main` registers this router via `api.py`, so
        # importing it at module load time here would be circular. By the
        # time a request is actually being handled, `app.main` has already
        # finished importing.
        from app.main import app

        _client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://copilot-internal")
    return _client


async def call_api(path: str, params: dict[str, Any] | None = None, *, auth_header: str | None = None) -> Any:
    """GETs one backend endpoint (under `/api/v1`) and returns its parsed
    JSON body. On failure, returns a structured `{"error": ...}` dict instead
    of raising — the LLM is told a tool call failed rather than being fed
    nothing and left to guess why.

    `auth_header` forwards the *asking user's own* bearer token (Milestone
    11: every endpoint now requires auth). The Copilot deliberately acts with
    the caller's own permissions, not some elevated service account — it
    should never be able to see more than the person asking it could see
    through the API directly.
    """
    client = await _get_client()
    full_path = f"/api/v1{path}"
    headers = {"Authorization": auth_header} if auth_header else None
    try:
        response = await client.get(full_path, params=params, headers=headers, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Copilot tool call failed: %s -> HTTP %s", full_path, exc.response.status_code)
        return {"error": f"{path} returned HTTP {exc.response.status_code}", "detail": exc.response.text[:300]}
    except Exception as exc:  # noqa: BLE001 - surfaced to the LLM as a tool failure, never raised
        logger.warning("Copilot tool call errored: %s -> %s", full_path, exc)
        return {"error": f"{path} could not be reached: {exc}"}
