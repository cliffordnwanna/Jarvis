import os
import redis.asyncio as aioredis

_client: aioredis.Redis | None = None


def get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    return _client


async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None
