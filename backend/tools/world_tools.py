import httpx
from langchain_core.tools import tool
from backend.db.cache import cache_get
from backend.db.postgres import get_supabase
from datetime import datetime, timezone


@tool
async def set_named_location(
    user_id: str,
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
async def get_nearby_places(lat: float, lng: float, place_type: str = "restaurant", radius: int = 2000) -> list:
    """
    Find places near the user's current location using OpenStreetMap (free).

    CALL THIS when user asks:
    - "Where can I eat nearby?"
    - "Is there a pharmacy near me?"
    - "Find me an ATM"
    - "What's near me?"
    - "Where's the nearest hospital/fuel station/bank/church?"

    place_type options: restaurant, cafe, hotel, hospital, pharmacy, atm, fuel,
                        bank, supermarket, church, mosque, school, police
    radius: search radius in meters (default 2000m = 2km)

    Returns list of places with name, lat, lng, and type.
    """
    type_map = {
        "restaurant": ("amenity", "restaurant"),
        "cafe":       ("amenity", "cafe"),
        "pharmacy":   ("amenity", "pharmacy"),
        "atm":        ("amenity", "atm"),
        "fuel":       ("amenity", "fuel"),
        "hospital":   ("amenity", "hospital"),
        "supermarket": ("shop", "supermarket"),
        "bank":       ("amenity", "bank"),
        "hotel":      ("tourism", "hotel"),
        "guest_house": ("tourism", "guest_house"),
        "church":     ("amenity", "place_of_worship"),
        "mosque":     ("amenity", "place_of_worship"),
        "school":     ("amenity", "school"),
        "police":     ("amenity", "police"),
    }
    tag_key, tag_val = type_map.get(place_type.lower(), ("amenity", place_type))

    query = f"""[out:json][timeout:15];
(
  node["{tag_key}"="{tag_val}"](around:{radius},{lat},{lng});
  way["{tag_key}"="{tag_val}"](around:{radius},{lat},{lng});
);
out center 8;"""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if r.status_code != 200:
                print(f"[get_nearby_places] Overpass HTTP {r.status_code}")
                return []
            data = r.json()
            results = []
            for el in data.get("elements", []):
                tags = el.get("tags", {})
                if not tags.get("name"):
                    continue
                el_lat = el.get("lat") or (el.get("center") or {}).get("lat")
                el_lng = el.get("lon") or (el.get("center") or {}).get("lon")
                if not el_lat or not el_lng:
                    continue
                results.append({
                    "name": tags["name"],
                    "type": place_type,
                    "lat": el_lat,
                    "lng": el_lng,
                    "address": tags.get("addr:street", ""),
                    "phone": tags.get("phone", ""),
                    "opening_hours": tags.get("opening_hours", ""),
                })
                if len(results) >= 8:
                    break
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
    Returns duration in minutes, distance in km, road waypoints for map drawing, and Lagos traffic note.
    """
    import pytz
    profiles = {"driving": "car", "walking": "foot", "cycling": "bike"}
    profile = profiles.get(mode, "car")

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"https://router.project-osrm.org/route/v1/{profile}/"
                f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}",
                params={"overview": "full", "geometries": "geojson"},
                timeout=10.0,
            )
            data = r.json()
            if data.get("code") == "Ok" and data.get("routes"):
                route       = data["routes"][0]
                duration_s  = route["duration"]
                distance_m  = route["distance"]
                raw_minutes = int(duration_s / 60)
                distance_km = round(distance_m / 1000, 1)

                # OSRM returns [lng, lat] pairs — swap to [lat, lng] for Leaflet
                coordinates = route.get("geometry", {}).get("coordinates", [])
                waypoints = [[c[1], c[0]] for c in coordinates]

                # Lagos traffic multiplier (OSRM uses speed limits, not real traffic)
                lagos_tz = pytz.timezone("Africa/Lagos")
                hour = datetime.now(lagos_tz).hour
                if 7 <= hour <= 10 or 17 <= hour <= 20:
                    traffic_factor = 2.5
                    traffic_note = "in current traffic (peak hours)"
                elif 6 <= hour <= 7 or 10 <= hour <= 12 or 15 <= hour <= 17:
                    traffic_factor = 1.8
                    traffic_note = "in current traffic"
                elif 22 <= hour or hour <= 5:
                    traffic_factor = 1.0
                    traffic_note = "at this hour (light traffic)"
                else:
                    traffic_factor = 1.4
                    traffic_note = "in normal traffic"

                realistic_minutes = int(raw_minutes * traffic_factor)

                return {
                    "duration_minutes": realistic_minutes,
                    "without_traffic_minutes": raw_minutes,
                    "traffic_note": traffic_note,
                    "distance_km": distance_km,
                    "mode": mode,
                    "waypoints": waypoints,
                    "origin": {"lat": origin_lat, "lng": origin_lng},
                    "destination": {"lat": dest_lat, "lng": dest_lng},
                    "summary": f"{realistic_minutes} min {traffic_note} ({distance_km} km)",
                }
        except Exception as e:
            print(f"[get_travel_eta] OSRM error: {e}")
        return {"error": "Route not available", "duration_minutes": None}
