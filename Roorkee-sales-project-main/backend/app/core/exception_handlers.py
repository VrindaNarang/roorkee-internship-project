"""Standardized error envelope for every failure response (Milestone 11).

Every error — a raised `HTTPException`, a Pydantic validation failure, or an
unhandled exception — comes back in the same shape:

    {"detail": <message or validation-error list>, "error_code": "...", "request_id": "..."}

`detail` is kept as the top-level key (FastAPI's own convention, and what
every `raise HTTPException(..., detail="...")` call across this codebase
already sets) so this is additive, not a breaking rename — `error_code` and
`request_id` are the new, consistently-present fields for API consumers/logs.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

_ERROR_CODE_BY_STATUS = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
    status.HTTP_502_BAD_GATEWAY: "UPSTREAM_ERROR",
    status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    status.HTTP_504_GATEWAY_TIMEOUT: "TIMEOUT",
}


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _envelope(detail: object, status_code: int, request: Request) -> dict:
    return {
        "detail": detail,
        "error_code": _ERROR_CODE_BY_STATUS.get(status_code, "HTTP_ERROR"),
        "request_id": _request_id(request),
    }


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.detail, exc.status_code, request),
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_envelope(exc.errors(), status.HTTP_422_UNPROCESSABLE_ENTITY, request),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_envelope("Internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR, request),
    )
