"""Tests for the in-process TTL cache (Milestone 11)."""

import time

from app.core.cache import clear_all, ttl_cache


def test_ttl_cache_returns_cached_value_within_ttl() -> None:
    calls = []

    @ttl_cache(seconds=5)
    def compute(db, value):
        calls.append(value)
        return value * 2

    assert compute("fake-db-session-1", 3) == 6
    assert compute("fake-db-session-2", 3) == 6  # different "db" object, same real args -> cache hit
    assert calls == [3]  # underlying function only actually ran once


def test_ttl_cache_expires_after_ttl() -> None:
    calls = []

    @ttl_cache(seconds=0.05)
    def compute(db, value):
        calls.append(value)
        return value * 2

    compute("db", 5)
    time.sleep(0.1)
    compute("db", 5)
    assert calls == [5, 5]  # second call recomputed after expiry


def test_ttl_cache_distinguishes_different_arguments() -> None:
    @ttl_cache(seconds=5)
    def compute(db, value):
        return value * 2

    assert compute("db", 1) == 2
    assert compute("db", 2) == 4


def test_clear_all_forces_recomputation() -> None:
    calls = []

    @ttl_cache(seconds=5)
    def compute(db, value):
        calls.append(value)
        return value

    compute("db", 42)
    clear_all()
    compute("db", 42)
    assert calls == [42, 42]
