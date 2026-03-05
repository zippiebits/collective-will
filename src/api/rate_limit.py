"""Lightweight in-process rate limiter for auth endpoints.

Uses a sliding-window counter per IP. This protects against brute-force
attempts on token verification and web-session exchange. For horizontal
scaling, replace with Redis-backed counters.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request


class _SlidingWindowCounter:
    """Per-key sliding window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        """Return True if request is allowed, False if rate-limited."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._hits[key]
            # Prune expired entries
            self._hits[key] = [t for t in timestamps if t > cutoff]
            if len(self._hits[key]) >= self.max_requests:
                return False
            self._hits[key].append(now)
            return True


# Auth endpoint rate limiters (per IP)
_verify_limiter = _SlidingWindowCounter(max_requests=10, window_seconds=60)
_web_session_limiter = _SlidingWindowCounter(max_requests=5, window_seconds=60)
_subscribe_limiter = _SlidingWindowCounter(max_requests=5, window_seconds=60)
_dispute_limiter = _SlidingWindowCounter(max_requests=3, window_seconds=3600)


def get_request_ip(request: Request) -> str:
    """Extract client IP, preferring CF-Connecting-IP over X-Forwarded-For."""
    # Cloudflare sets this header and it cannot be spoofed behind CF
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the last IP (closest to the reverse proxy) for safety,
        # but if behind a single trusted proxy, first is the real client.
        # Using first here since Caddy is configured with trusted_proxies.
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def enforce_verify_rate_limit(request: Request) -> None:
    ip = get_request_ip(request)
    if not _verify_limiter.check(ip):
        raise HTTPException(status_code=429, detail="rate_limit_exceeded")


def enforce_web_session_rate_limit(request: Request) -> None:
    ip = get_request_ip(request)
    if not _web_session_limiter.check(ip):
        raise HTTPException(status_code=429, detail="rate_limit_exceeded")


def enforce_subscribe_rate_limit(request: Request) -> None:
    ip = get_request_ip(request)
    if not _subscribe_limiter.check(ip):
        raise HTTPException(status_code=429, detail="rate_limit_exceeded")


def enforce_dispute_rate_limit(user_id: str) -> None:
    if not _dispute_limiter.check(user_id):
        raise HTTPException(status_code=429, detail="rate_limit_exceeded")


# Voice verification rate limiter (per user_id)
_voice_verify_limiter = _SlidingWindowCounter(max_requests=5, window_seconds=3600)


def check_voice_rate_limit(user_id: str) -> bool:
    """Return True if voice verification attempt is allowed, False if rate-limited."""
    return _voice_verify_limiter.check(user_id)
