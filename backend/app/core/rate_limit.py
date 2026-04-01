"""Minimal in-memory rate limiting for sensitive endpoints."""

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import time


@dataclass(frozen=True)
class RateLimitStatus:
    """Result of checking a rate limit bucket."""
    allowed: bool
    retry_after_seconds: int
    remaining: int


class InMemoryRateLimiter:
    """Simple per-key sliding-window rate limiter for single-process deployments."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitStatus:
        now = time()
        window_start = now - window_seconds

        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, int(bucket[0] + window_seconds - now))
                return RateLimitStatus(
                    allowed=False,
                    retry_after_seconds=retry_after,
                    remaining=0,
                )

            bucket.append(now)
            remaining = max(0, limit - len(bucket))
            return RateLimitStatus(
                allowed=True,
                retry_after_seconds=0,
                remaining=remaining,
            )


auth_rate_limiter = InMemoryRateLimiter()
