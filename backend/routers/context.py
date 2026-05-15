from __future__ import annotations

import json
import os
import time
import uuid

import asyncpg
import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from backend.nudge_engine import evaluate as run_nudge_engine
from backend.world_state import build_world_state

router = APIRouter(prefix="/context", tags=["context"])


class DevicePayload(BaseModel):
    battery_pct: float = 100
    charging: bool = False
    headphones_connected: bool = False
    network_type: str = "unknown"
    platform: str = "web"
    screen_on: bool = True


class ContextRequest(BaseModel):
    user_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    device: DevicePayload
    behavioral: dict | None = None
    timezone: str | None = None


async def _ip_geolocation(ip: str) -> tuple[float, float] | None:
    """Free IP-based geolocation via ipapi.co (fallback when GPS is unavailable)."""
    try:
        lookup_ip = ip if ip not in ("127.0.0.1", "::1") else ""
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"https://ipapi.co/{lookup_ip}json/")
            data = resp.json()
            lat = data.get("latitude")
            lng = data.get("longitude")
            if lat and lng:
                return float(lat), float(lng)
    except Exception:
        pass
    return None


async def _fetch_active_goals(user_id: str) -> list[dict]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return []

    conn = await asyncpg.connect(database_url.replace("+asyncpg", ""))
    try:
        rows = await conn.fetch(
            "SELECT id, name, status, urgency, last_touched_at FROM goals WHERE user_id=$1 AND status='active'",
            user_id,
        )
        goals: list[dict] = []
        for r in rows:
            goals.append(
                {
                    "id": str(r["id"]),
                    "name": r["name"],
                    "status": r["status"],
                    "urgency": r["urgency"],
                    "last_touched": r["last_touched_at"].isoformat() if r["last_touched_at"] else None,
                    "days_since_touched": 0,
                }
            )
        return goals
    finally:
        await conn.close()


async def _should_enrich(r, user_id: str, min_interval_s: int = 30) -> bool:
    """
    Prevent runaway enrichment (many expensive API calls) when the frontend
    posts sensor payloads frequently or when requests overlap.
    """
    # Only one enrichment at a time per user
    lock_key = f"enrich_lock:{user_id}"
    got_lock = await r.set(lock_key, "1", nx=True, ex=30)
    if not got_lock:
        return False

    last_key = f"last_enrich_ts:{user_id}"
    last_raw = await r.get(last_key)
    now = time.time()
    if last_raw:
        try:
            last = float(last_raw)
            if now - last < float(min_interval_s):
                return False
        except ValueError:
            pass

    await r.setex(last_key, 3600, str(now))
    return True


@router.post("")
async def receive_context(request: Request, body: ContextRequest, enrich: bool = Query(default=True)):
    """
    Called by the PWA when sensors change.

    Think + Act loop:
      payload -> world_state enrichment -> nudge engine -> cache results
    """
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    user_id = body.user_id or "default"

    raw_payload = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    try:
        await r.setex(f"sensor_payload:{user_id}", 300, json.dumps(raw_payload))
    except Exception:
        await r.aclose()
        return {
            "status": "redis_down",
            "user_id": user_id,
            "message": "Redis is not reachable. Start Redis (docker-compose) then retry.",
        }

    if not enrich:
        await r.aclose()
        return {"status": "cached", "user_id": user_id}

    if not await _should_enrich(r, user_id=user_id, min_interval_s=30):
        await r.aclose()
        return {"status": "cached_busy", "user_id": user_id}

    behavioral = body.behavioral or {
        "timezone": body.timezone or os.getenv("DEFAULT_TIMEZONE", "Africa/Lagos")
    }
    db_goals = await _fetch_active_goals(user_id) if body.user_id else []

    lat = body.lat
    lng = body.lng
    if lat is None or lng is None:
        client_ip = request.client.host if request.client else "127.0.0.1"
        coords = await _ip_geolocation(client_ip)
        if coords:
            lat, lng = coords

    if lat is None or lng is None:
        world_state = {
            "device": body.device.model_dump() if hasattr(body.device, "model_dump") else body.device.dict(),
            "temporal": {"timestamp": __import__("datetime").datetime.now().isoformat()},
        }
    else:
        world_state = await build_world_state(
            lat=lat,
            lng=lng,
            device_payload=body.device.model_dump() if hasattr(body.device, "model_dump") else body.device.dict(),
            location_history=[],
            behavioral=behavioral,
            db_goals=db_goals,
            llm_client=None,
        )

    nudges = run_nudge_engine(world_state=world_state, goals=db_goals)

    # Ensure nudges have ids and store them in a way /nudges can read.
    normalized_nudges: list[dict] = []
    for n in nudges:
        if not isinstance(n, dict):
            continue
        nudge_id = n.get("id") or str(uuid.uuid4())
        n = {**n, "id": nudge_id}
        normalized_nudges.append(n)
        await r.setex(f"nudge:{nudge_id}", 900, json.dumps(n, default=str))
        await r.sadd("nudge_ids", nudge_id)

    panel_open = any(n.get("priority") == "high" for n in normalized_nudges)

    # Back-compat keys (single-user local dev) + user-scoped keys.
    await r.setex("world_state", 300, json.dumps(world_state, default=str))
    await r.setex(f"world_state:{user_id}", 300, json.dumps(world_state, default=str))

    await r.setex("nudges", 300, json.dumps(normalized_nudges, default=str))
    await r.setex(f"nudges:{user_id}", 300, json.dumps(normalized_nudges, default=str))

    await r.setex("panel_open", 300, json.dumps(panel_open))
    await r.setex(f"panel_open:{user_id}", 300, json.dumps(panel_open))

    await r.aclose()
    return {"status": "ok", "user_id": user_id, "nudges": normalized_nudges}


@router.get("/latest")
async def latest(user_id: str = "default"):
    """Debug endpoint: read the latest cached state for a user."""
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    try:
        ws = await r.get(f"world_state:{user_id}")
        nudges = await r.get(f"nudges:{user_id}")
        panel_open = await r.get(f"panel_open:{user_id}")
        return {
            "user_id": user_id,
            "world_state": json.loads(ws) if ws else None,
            "nudges": json.loads(nudges) if nudges else [],
            "panel_open": json.loads(panel_open) if panel_open else False,
        }
    finally:
        await r.aclose()

