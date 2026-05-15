import os
import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        url = os.getenv("DATABASE_URL", "postgresql://jarvis:jarvis@localhost:5432/jarvis").replace("+asyncpg", "")
        _pool = await asyncpg.create_pool(url)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
