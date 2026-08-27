"""Minimal in-process TTL cache for expensive, frequently-repeated read
queries (Milestone 11's performance ask).

Deliberately not Redis: this backend runs as a single process with no
horizontal scaling yet, so a process-local cache is simpler and sufficient —
swapping in Redis later means changing this one module, not every call site.

The first positional argument to every cached function in this codebase is
always either a SQLAlchemy `Session` (`db`) or a service instance (`self`
holding one) — a fresh object every request, but not something that changes
what a query returns. It's excluded from the cache key on that basis.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_store: dict[tuple, tuple[float, Any]] = {}


def ttl_cache(seconds: float) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = (
                func.__module__,
                func.__qualname__,
                args[1:],  # drop db/self — see module docstring
                tuple(sorted(kwargs.items())),
            )
            now = time.monotonic()
            cached = _store.get(cache_key)
            if cached is not None and cached[0] > now:
                return cached[1]
            result = func(*args, **kwargs)
            _store[cache_key] = (now + seconds, result)
            return result

        wrapper.cache_clear = _store.clear  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


def clear_all() -> None:
    """Invalidates every cached entry — called after a retrain/recalculate
    so the next read reflects fresh model output immediately rather than
    waiting out the TTL."""
    _store.clear()
