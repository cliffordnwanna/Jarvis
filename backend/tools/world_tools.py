from typing import Annotated
import httpx
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from backend.db.cache import cache_get
from backend.db.postgres import get_supabase
from datetime import datetime, timezone


@tool
async def set_named_location(
    user_id: Annotated[str, InjectedState("user_id")],
    location_type: str,
    address: str = None,
    lat: float = None,
    lng: float = None,
) -> dict:
    """
    Save a named location (home, work, gym, etc.) for the user.

    CALL THIS when user says:
    - "Set this as my home" / "Save my location as home"
    - "My work address is X" / "Save X as my office"
    - "Remember this place as X"
    - "Set home to [address]"

    If address is given but no coordinates, geocodes it automatically.
    If neither address nor coordinates are given, uses current GPS location.

    Args:
        user_id: The user's ID
        location_type: home, work, gym, or any custom label
        address: Human-readable address (geocoded if no lat/lng provided)
        lat: Latitude (optional if address given)
        lng: Longitude (optional if address given)
    """
    from backend.main import bust_profile_cache
    db = get_supabase()

    resolved_lat = lat
    resolved_lng = lng
    resolved_address = address

    # Geocode address if coordinates not provided
    if address and (not resolved_lat or not resolved_lng):
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": address + ", Lagos, Nigeria", "format": "json", "limit": 1},
                    headers={"User-Agent": "JARVIS/1.0"},
                    timeout=8.0,
                )
                results = r.json()
                if results:
                    resolved_lat = float(results[0]["lat"])
                    resolved_lng = float(results[0]["lon"])
                    resolved_address = results[0].get("display_name", address)
                else:
                    return {"error": f"Could not find '{address}' on the map"}
        except Exception as e:
            return {"error": f"Geocoding failed: {e}"}

    # Fall back to current GPS from cache
    if not resolved_lat or not resolved_lng:
        ws = await cache_get(user_id)
        if ws:
            loc = ws.get("location", {})
            resolved_lat = loc.get("lat") or ws.get("_meta", {}).get("lat")
            resolved_lng = loc.get("lng") or ws.get("_meta", {}).get("lng")
            district = loc.get("district", "")
            city = loc.get("city", "")
            resolved_address = f"{district}, {city}" if district and district != city else city

    if not resolved_lat or not resolved_lng:
        return {"error": "Could not determine location coordinates"}

    lt = location_type.lower()
    if lt in ("home", "house"):
        db.table("users").update({
            "home_lat": resolved_lat,
            "home_lng": resolved_lng,
            "home_address": resolved_address,
        }).eq("id", user_id).execute()
    elif lt in ("work", "office", "job"):
        db.table("users").update({
            "work_lat": resolved_lat,
            "work_lng": resolved_lng,
            "work_address": resolved_address,
        }).eq("id", user_id).execute()
    else:
        try:
            existing = db.table("users").select("named_locations")\
                .eq("id", user_id).maybe_single().execute()
            named = (existing.data or {}).get("named_locations") or {}
            named[lt] = {"lat": resolved_lat, "lng": resolved_lng, "address": resolved_address}
            db.table("users").update({"named_locations": named}).eq("id", user_id).execute()
        except Exception as e:
            return {"error": f"Could not save custom location: {e}"}

    bust_profile_cache(user_id)

    return {
        "status": "saved",
        "location_type": location_type,
        "address": resolved_address,
        "lat": resolved_lat,
        "lng": resolved_lng,
    }


@tool
def create_timer(label: str, seconds: int) -> str:
    """
    Create a countdown timer that appears in the user's chat interface.

    CALL THIS when user says:
    - "set a timer for X seconds/minutes/hours"
    - "timer for my pasta / tea / workout"
    - "count down X minutes"
    - Any request for a countdown timer

    Args:
        label: Short description e.g. "pasta", "tea break", "10 second timer"
        seconds: Duration in seconds. Convert naturally:
                 "30 seconds"          → 30
                 "2 minutes"           → 120
                 "1 hour"              → 3600
                 "1 minute 30 seconds" → 90

    Returns a sentinel string the frontend uses to render an inline countdown.
    """
    return f"__TIMER__:{seconds}:{label}"


@tool
async def get_world_state(user_id: Annotated[str, InjectedState("user_id")]) -> dict:
    """
    Get the user's current real-world context including location, weather, and time.

    CALL THIS when the user asks about:
    - Current weather or temperature
    - What time or day it is
    - Their current location
    - Whether to bring an umbrella
    - Any location-aware recommendation

    Returns location (city, district, country), weather (temp, condition,
    rain probability), and time (hour, day, timezone).
    """
    state = await cache_get(user_id)
    if not state:
        return {"error": "No world state available. User needs to grant location permission and POST to /context/update."}
    return state


@tool
async def send_nudge(
    user_id: Annotated[str, InjectedState("user_id")],
    nudge_type: str,
    message: str,
    priority: str = "medium",
    person_id: str = None,
) -> dict:
    """
    Send a proactive nudge/notification that appears in the user's nudge panel.

    CALL THIS when you want to:
    - Alert the user about something important
    - Add a task or reminder to their nudge panel immediately
    - Surface a relationship alert (birthday, overdue contact)
    - Flag a weather warning or goal reminder

    nudge_type options: weather, goal, relationship_birthday,
                        relationship_cooling, relationship_followup, general
    priority options: low, medium, high
    """
    db = get_supabase()
    data = {
        "user_id": user_id,
        "nudge_type": nudge_type,
        "message": message,
        "priority": priority,
        "delivered_at": datetime.now(timezone.utc).isoformat(),
    }
    if person_id:
        data["person_id"] = person_id
    db.table("nudge_history").insert(data).execute()
    return {"status": "nudge_sent", "message": message}


