import os
import pytz
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from backend.auth import get_current_user
from backend.db.cache import cache_set, cache_get
from backend.db.postgres import get_supabase
from backend.nudge_engine import evaluate_nudges
from backend.world_state import build_world_state

router = APIRouter()


class SensorPayload(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    timezone: Optional[str] = "Africa/Lagos"
    device: Optional[dict] = {}
    behavioral: Optional[dict] = {}


@router.post("/update")
async def update_context(
    payload: SensorPayload,
    user_id: str = Depends(get_current_user),
):
    """Receive sensor data, build world state, evaluate nudges, cache result."""
    lat = payload.lat
    lng = payload.lng

    # IP geolocation fallback when GPS not provided
    if not lat or not lng:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://ip-api.com/json")
                data = resp.json()
                lat = data.get("lat", 6.5244)
                lng = data.get("lon", 3.3792)
        except Exception:
            lat, lng = 6.5244, 3.3792  # Lagos default

    behavioral = payload.behavioral or {}
    behavioral["timezone"] = payload.timezone or os.getenv("DEFAULT_TIMEZONE", "Africa/Lagos")

    # Fetch active goals from DB
    db = get_supabase()
    goals_res = db.table("goals").select("*").eq("user_id", user_id).eq("status", "active").execute()
    db_goals = goals_res.data or []

    # Fetch upcoming relationship events
    try:
        tz = pytz.timezone(payload.timezone or "Africa/Lagos")
        now_local = datetime.now(tz).isoformat()
        events_res = db.table("relationship_events") \
            .select("*, people(name)") \
            .eq("user_id", user_id) \
            .is_("completed_at", "null") \
            .gte("scheduled_at", now_local) \
            .order("scheduled_at") \
            .limit(10) \
            .execute()
        upcoming_events = events_res.data or []
    except Exception:
        upcoming_events = []

    world_state = await build_world_state(
        lat=lat,
        lng=lng,
        device_payload=payload.device or {},
        location_history=[],
        behavioral=behavioral,
        db_goals=db_goals,
    )

    world_state["user_id"] = user_id
    world_state["upcoming_relationship_events"] = upcoming_events

    await cache_set(user_id, world_state)

    nudges = await evaluate_nudges(world_state, user_id)

    return {
        "status": "ok",
        "nudges_generated": len(nudges),
        "location": world_state.get("location", {}),
        "weather": world_state.get("environment", {}).get("weather", {}),
    }


@router.get("/latest")
async def get_latest(user_id: str = Depends(get_current_user)):
    state = await cache_get(user_id)
    if not state:
        return {"status": "empty", "message": "No world state yet. POST to /context/update first."}
    return state
