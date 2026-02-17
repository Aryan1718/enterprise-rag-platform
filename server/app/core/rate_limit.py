from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from redis import Redis
from redis.exceptions import RedisError

from app.config import settings

QUERY_RATE_LIMIT = 100
QUERY_RATE_WINDOW_SECONDS = 60

_redis_client: Redis | None = None


def _redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def enforce_query_rate_limit(workspace_id: uuid.UUID) -> None:
    key = f"rate_limit:query:{workspace_id}"
    try:
        count = int(_redis().incr(key))
        if count == 1:
            _redis().expire(key, QUERY_RATE_WINDOW_SECONDS)
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Rate limiter unavailable: {exc}",
        ) from exc
    if count > QUERY_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Query rate limit exceeded",
        )
