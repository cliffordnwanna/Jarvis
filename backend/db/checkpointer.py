"""
LangGraph conversation persistence via PostgresSaver.
Conversations survive browser refresh and server restarts.
"""
from __future__ import annotations
import os
from typing import Optional
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

_pool: Optional[AsyncConnectionPool] = None
_checkpointer: Optional[AsyncPostgresSaver] = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return the singleton checkpointer, creating it on first call."""
    global _pool, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise ValueError("DATABASE_URL must be set (Supabase Project Settings → Database → Connection string)")

    conn_string = (
        database_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )

    _pool = AsyncConnectionPool(
        conninfo=conn_string,
        max_size=10,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
        },
        open=False,
    )
    await _pool.open()

    _checkpointer = AsyncPostgresSaver(_pool)
    await _checkpointer.setup()  # creates checkpoint tables if they don't exist

    return _checkpointer


async def close_checkpointer() -> None:
    """Gracefully close the connection pool on shutdown."""
    global _pool, _checkpointer
    if _pool:
        await _pool.close()
    _pool = None
    _checkpointer = None
