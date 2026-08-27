"""Cross-cutting request middleware (Milestone 11): a request ID on every
request/response pair, and one structured access-log line per request.

Kept separate from `app/main.py` so the app-assembly file stays a thin
wiring list, and separate from `exception_handlers.py` (which reacts to
failures) — this module's job is purely "observe every request", success or
failure alike.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.request")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request ID (reusing one supplied by an upstream proxy if
    present, so traces stay joined across a load balancer), times the
    request, and logs one line per response — the log level follows the
    status code (5xx -> error, 4xx -> warning, else info) so `grep`-ing logs
    for real problems doesn't require parsing every line.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        request.state.request_id = request_id
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id

        log_line = "%s %s -> %s (%.2fms) [%s]"
        log_args = (request.method, request.url.path, response.status_code, duration_ms, request_id)
        if response.status_code >= 500:
            logger.error(log_line, *log_args)
        elif response.status_code >= 400:
            logger.warning(log_line, *log_args)
        else:
            logger.info(log_line, *log_args)

        return response
