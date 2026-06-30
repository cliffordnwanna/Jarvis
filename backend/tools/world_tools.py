import httpx
from langchain_core.tools import tool
from backend.db.cache import cache_get
from backend.db.postgres import get_supabase
from datetime import datetime, timezone


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
async def get_world_state(user_id: str) -> dict:
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
    user_id: str,
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


@tool
async def get_nearby_places(lat: float, lng: float, place_type: str = "restaurant", radius: int = 1000) -> list:
    """
    Find places near the user's current location using OpenStreetMap (free).

    CALL THIS when user asks:
    - "Where can I eat nearby?"
    - "Is there a pharmacy near me?"
    - "Find me an ATM"
    - "What's near me?"
    - "Where's the nearest hospital/fuel station/bank?"

    place_type options: restaurant, cafe, hotel, hospital, pharmacy, atm, fuel, bank, supermarket
    radius: search radius in meters (default 1000m = 1km)

    Returns list of places with name, type, and coordinates.
    """
    type_map = {
        "restaurant": ("amenity", "restaurant"),
        "cafe": ("amenity", "cafe"),
        "pharmacy": ("amenity", "pharmacy"),
        "atm": ("amenity", "atm"),
        "fuel": ("amenity", "fuel"),
        "hospital": ("amenity", "hospital"),
        "supermarket": ("shop", "supermarket"),
        "bank": ("amenity", "bank"),
        "hotel": ("tourism", "hotel"),
        "guest_house": ("tourism", "guest_house"),
    }
    tag_key, tag_val = type_map.get(place_type.lower(), ("amenity", place_type))

    query = f"""[out:json][timeout:15];
(
  node["{tag_key}"="{tag_val}"](around:{radius},{lat},{lng});
  way["{tag_key}"="{tag_val}"](around:{radius},{lat},{lng});
);
out center 10;"""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if r.status_code != 200:
                return []
            data = r.json()
            results = []
            for el in data.get("elements", [])[:8]:
                tags = el.get("tags", {})
                if not tags.get("name"):
                    continue
                el_lat = el.get("lat") or (el.get("center") or {}).get("lat")
                el_lng = el.get("lon") or (el.get("center") or {}).get("lon")
                results.append({
                    "name": tags["name"],
                    "type": place_type,
                    "lat": el_lat,
                    "lng": el_lng,
                    "address": tags.get("addr:street", ""),
                    "phone": tags.get("phone", ""),
                    "opening_hours": tags.get("opening_hours", ""),
                })
            return results
    except Exception as e:
        print(f"[get_nearby_places] error: {e}")
        return []


@tool
async def get_travel_eta(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    mode: str = "driving",
) -> dict:
    """
    Calculate travel time between two locations using OSRM (free).

    CALL THIS when user asks:
    - "How long will it take to get to work?"
    - "What's the travel time from X to Y?"
    - "How far is it to [location]?"
    - "Should I leave now to make it in time?"

    mode options: driving, walking, cycling
    Returns duration in minutes and distance in km.
    """
    profiles = {"driving": "car", "walking": "foot", "cycling": "bike"}
    profile = profiles.get(mode, "car")

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"https://router.project-osrm.org/route/v1/{profile}/"
                f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}",
                params={"overview": "false", "steps": "false"},
                timeout=8.0,
            )
            data = r.json()
            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                duration_mins = round(route["duration"] / 60)
                distance_km = round(route["distance"] / 1000, 1)
                return {
                    "duration_minutes": duration_mins,
                    "distance_km": distance_km,
                    "mode": mode,
                    "summary": f"{duration_mins} min by {mode} ({distance_km} km)",
                }
        except Exception as e:
            print(f"[get_travel_eta] OSRM error: {e}")
        return {"error": "Route not available", "duration_minutes": None}
