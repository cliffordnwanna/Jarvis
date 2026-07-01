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


def _decode_google_polyline(encoded: str) -> list:
    """Decode Google Encoded Polyline Algorithm to [[lat, lng], ...] pairs."""
    result = []
    index = lat = lng = 0
    while index < len(encoded):
        for is_lat in (True, False):
            shift = result_val = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result_val |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result_val >> 1) if result_val & 1 else result_val >> 1
            if is_lat:
                lat += delta
            else:
                lng += delta
        result.append([lat / 1e5, lng / 1e5])
    return result


@tool
async def get_nearby_places(
    user_id: str,
    place_type: str = "restaurant",
    radius: int = 2000,
) -> list:
    """
    Find nearby places using Google Places API (best Nigeria/Lagos coverage).

    CALL THIS when user asks:
    - "Where can I eat nearby?" / "Find a restaurant near me"
    - "Is there a pharmacy/ATM/bank/hospital near me?"
    - "Find a church / mosque near me"
    - "What's near me?"
    - "Where's the nearest fuel station/supermarket?"

    place_type options: restaurant, cafe, hotel, hospital, pharmacy, atm, fuel,
                        bank, church, mosque, supermarket, school, police, gym
    radius: search radius in meters (default 2000m = 2km)

    Returns list of places with name, lat, lng, distance, rating, and address.
    """
    import os, math
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "Google Maps API key not configured"}]

    ws = await cache_get(user_id)
    if not ws:
        return [{"error": "No location available"}]

    location = ws.get("location", {})
    lat = location.get("lat") or ws.get("_meta", {}).get("lat")
    lng = location.get("lng") or ws.get("_meta", {}).get("lng")
    if not lat or not lng:
        return [{"error": "Could not determine your location"}]

    type_map = {
        "restaurant":  "restaurant",
        "cafe":        "cafe",
        "fastfood":    "meal_takeaway",
        "hotel":       "lodging",
        "hospital":    "hospital",
        "pharmacy":    "pharmacy",
        "atm":         "atm",
        "fuel":        "gas_station",
        "bank":        "bank",
        "church":      "church",
        "mosque":      "mosque",
        "supermarket": "supermarket",
        "school":      "school",
        "police":      "police",
        "gym":         "gym",
        "parking":     "parking",
    }
    gtype = type_map.get(place_type.lower(), place_type)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params={
                    "location": f"{lat},{lng}",
                    "radius": radius,
                    "type": gtype,
                    "key": api_key,
                    "rankby": "prominence",
                },
            )
            if r.status_code != 200:
                print(f"[get_nearby_places] Google HTTP {r.status_code}: {r.text[:200]}")
                return []
            data = r.json()

        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            print(f"[get_nearby_places] Google error: {status} — {data.get('error_message', '')}")
            return [{"error": f"Google Places error: {status}"}]

        results = []
        for place in data.get("results", [])[:8]:
            loc = place.get("geometry", {}).get("location", {})
            p_lat = loc.get("lat")
            p_lng = loc.get("lng")
            if not p_lat or not p_lng:
                continue

            dlat = math.radians(p_lat - lat)
            dlng = math.radians(p_lng - lng)
            a = (math.sin(dlat / 2) ** 2
                 + math.cos(math.radians(lat)) * math.cos(math.radians(p_lat))
                 * math.sin(dlng / 2) ** 2)
            dist_m = int(6371000 * 2 * math.asin(math.sqrt(a)))
            dist_str = f"{round(dist_m / 1000, 1)} km" if dist_m >= 1000 else f"{dist_m} m"

            rating = place.get("rating", "")
            results.append({
                "name": place.get("name", "Unknown"),
                "lat": p_lat,
                "lng": p_lng,
                "type": place_type,
                "distance_m": dist_m,
                "distance_str": dist_str,
                "address": place.get("vicinity", ""),
                "rating": rating,
                "open_now": place.get("opening_hours", {}).get("open_now"),
                "display": f"{place.get('name')}{f' ⭐{rating}' if rating else ''} — {dist_str}",
            })

        results.sort(key=lambda x: x["distance_m"])
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
    Get accurate travel time with real Lagos traffic using Google Directions API.

    CALL THIS when user asks:
    - "How long will it take to get to work?"
    - "What's the travel time from X to Y?"
    - "How far is it to [location]?"
    - "Should I leave now to make it in time?"

    mode options: driving, walking, bicycling, transit
    Returns duration in minutes, distance in km, road waypoints for the map, traffic note.
    """
    import os
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "Google Maps API key not configured"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://maps.googleapis.com/maps/api/directions/json",
                params={
                    "origin": f"{origin_lat},{origin_lng}",
                    "destination": f"{dest_lat},{dest_lng}",
                    "mode": mode,
                    "departure_time": "now",
                    "traffic_model": "best_guess",
                    "key": api_key,
                },
            )
            if r.status_code != 200:
                print(f"[get_travel_eta] Google HTTP {r.status_code}: {r.text[:200]}")
                return {"error": "Route not available", "duration_minutes": None}
            data = r.json()

        if data.get("status") != "OK":
            return {"error": f"Directions error: {data.get('status')}", "duration_minutes": None}

        leg = data["routes"][0]["legs"][0]

        if "duration_in_traffic" in leg:
            duration_s = leg["duration_in_traffic"]["value"]
            traffic_note = "with current traffic"
        else:
            duration_s = leg["duration"]["value"]
            traffic_note = "estimated"

        distance_m = leg["distance"]["value"]
        minutes = int(duration_s / 60)
        km = round(distance_m / 1000, 1)

        encoded = data["routes"][0].get("overview_polyline", {}).get("points", "")
        waypoints = _decode_google_polyline(encoded) if encoded else [
            [origin_lat, origin_lng],
            [dest_lat, dest_lng],
        ]

        return {
            "duration_minutes": minutes,
            "distance_km": km,
            "traffic_note": traffic_note,
            "mode": mode,
            "waypoints": waypoints,
            "origin": {"lat": origin_lat, "lng": origin_lng},
            "destination": {"lat": dest_lat, "lng": dest_lng},
            "summary": f"{minutes} min {traffic_note} ({km} km)",
        }
    except Exception as e:
        print(f"[get_travel_eta] error: {e}")
        return {"error": str(e), "duration_minutes": None}
