from fastapi import Request, HTTPException
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

_request_counts: dict = defaultdict(list)
_lock = asyncio.Lock()

# 60 requests per minute per IP
# Voice endpoint gets more headroom — 120/min
LIMITS = {
    "default": (60, 60),
    "/voice": (120, 60),
    "/health": None,
}


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path

    if path == "/health":
        return await call_next(request)

    limit_key = "/voice" if path.startswith("/voice") else "default"
    max_requests, window_seconds = LIMITS[limit_key]

    client_ip = request.client.host
    cache_key = f"{client_ip}:{limit_key}"
    now = datetime.now()
    window_start = now - timedelta(seconds=window_seconds)

    async with _lock:
        _request_counts[cache_key] = [
            t for t in _request_counts[cache_key] if t > window_start
        ]

        if len(_request_counts[cache_key]) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s."
            )

        _request_counts[cache_key].append(now)

    return await call_next(request)
