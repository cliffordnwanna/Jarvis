import json
import os
from fastapi import APIRouter, HTTPException
import redis.asyncio as aioredis

router = APIRouter(prefix="/nudges", tags=["nudges"])


async def _redis():
    return aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


@router.get("")
async def get_nudges():
    """Return all pending nudges. Frontend polls this every 10s."""
    r = await _redis()
    try:
        try:
            ids = await r.smembers("nudge_ids")
        except Exception:
            return []
        nudges = []
        dead_ids = []
        for nid in ids:
            raw = await r.get(f"nudge:{nid.decode()}")
            if raw:
                nudges.append(json.loads(raw))
            else:
                dead_ids.append(nid)
        # Clean up expired ids from the set
        if dead_ids:
            await r.srem("nudge_ids", *dead_ids)
        # Sort: high priority first
        priority_order = {"high": 0, "medium": 1, "low": 2}
        nudges.sort(key=lambda n: priority_order.get(n.get("priority", "low"), 3))
        return nudges
    finally:
        await r.aclose()


@router.delete("/{nudge_id}")
async def dismiss_nudge(nudge_id: str):
    """Dismiss a nudge — called when user swipes/clicks dismiss in the UI."""
    r = await _redis()
    try:
        deleted = await r.delete(f"nudge:{nudge_id}")
        await r.srem("nudge_ids", nudge_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Nudge not found")
        return {"status": "dismissed", "id": nudge_id}
    finally:
        await r.aclose()


@router.delete("")
async def clear_all_nudges():
    """Clear all nudges — useful for testing."""
    r = await _redis()
    try:
        ids = await r.smembers("nudge_ids")
        if ids:
            keys = [f"nudge:{nid.decode()}" for nid in ids]
            await r.delete(*keys)
            await r.delete("nudge_ids")
        return {"status": "cleared", "count": len(ids)}
    finally:
        await r.aclose()
