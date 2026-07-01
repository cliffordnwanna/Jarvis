"""
JARVIS Google Maps Tools
All location intelligence powered by Google Maps Platform.
"""
import os
import httpx
import math
from langchain_core.tools import tool
from backend.db.cache import cache_get
from backend.db.postgres import get_supabase


def _haversine(lat1, lng1, lat2, lng2) -> int:
    """Distance in meters between two coordinates."""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return int(R * 2 * math.asin(math.sqrt(a)))


def _decode_polyline(encoded: str) -> list:
    """Decode Google Encoded Polyline to [[lat, lng], ...] pairs."""
    result = []
    index = lat = lng = 0
    while index < len(encoded):
        for is_lat in (True, False):
            shift = val = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                val |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(val >> 1) if val & 1 else val >> 1
            if is_lat:
                lat += delta
            else:
                lng += delta
        result.append([lat / 1e5, lng / 1e5])
    return result


async def _get_user_location(user_id: str):
    """Return (lat, lng) from world state cache, or (None, None)."""
    ws = await cache_get(user_id)
    if not ws:
        return None, None
    loc = ws.get("location", {})
    lat = loc.get("lat") or ws.get("_meta", {}).get("lat")
    lng = loc.get("lng") or ws.get("_meta", {}).get("lng")
    return lat, lng


@tool
async def find_nearby_places(
    user_id: str,
    query: str,
    radius: int = 3000,
) -> list:
    """
    Find any nearby place using Google Maps Places API.

    ALWAYS use this when user asks to find ANYTHING nearby.
    The query accepts natural language — not just hardcoded types.

    Examples:
    - "find a restaurant near me"      → query="restaurant"
    - "find a church near me"          → query="church"
    - "is there a Shoprite nearby?"    → query="Shoprite"
    - "find somewhere to buy suya"     → query="suya spot"
    - "find a filling station"         → query="fuel station"
    - "find a mechanic"                → query="auto repair"
    - "find a pharmacy"                → query="pharmacy"
    - "find an ATM"                    → query="ATM"
    - "find a hotel"                   → query="hotel"

    Args:
        user_id: The user's UUID
        query: Natural language description of what to find
        radius: Search radius in meters (default 3000 = 3km)
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "Google Maps not configured"}]

    lat, lng = await _get_user_location(user_id)
    if not lat:
        return [{"error": "Location not available"}]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try Places API (New) first — better results
            r = await client.post(
                "https://places.googleapis.com/v1/places:searchNearby",
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": (
                        "places.displayName,places.formattedAddress,"
                        "places.location,places.rating,places.userRatingCount,"
                        "places.currentOpeningHours,places.nationalPhoneNumber,"
                        "places.businessStatus"
                    ),
                },
                json={
                    "textQuery": query,
                    "locationRestriction": {
                        "circle": {
                            "center": {"latitude": lat, "longitude": lng},
                            "radius": float(radius),
                        }
                    },
                    "maxResultCount": 8,
                    "rankPreference": "DISTANCE",
                },
            )
            data = r.json()
            places_new = data.get("places", [])

        if places_new:
            results = []
            for p in places_new:
                loc = p.get("location", {})
                p_lat = loc.get("latitude")
                p_lng = loc.get("longitude")
                if not p_lat or not p_lng:
                    continue
                dist = _haversine(lat, lng, p_lat, p_lng)
                dist_str = f"{round(dist / 1000, 1)} km" if dist >= 1000 else f"{dist} m"
                rating = p.get("rating", "")
                is_open = p.get("currentOpeningHours", {}).get("openNow")
                results.append({
                    "name": p.get("displayName", {}).get("text", "Unknown"),
                    "lat": p_lat,
                    "lng": p_lng,
                    "distance_m": dist,
                    "distance_str": dist_str,
                    "address": p.get("formattedAddress", ""),
                    "rating": rating,
                    "open_now": is_open,
                    "open_str": "Open now" if is_open else ("Closed" if is_open is False else ""),
                    "phone": p.get("nationalPhoneNumber", ""),
                    "display": f"{p.get('displayName', {}).get('text', 'Unknown')}{f' ⭐{rating}' if rating else ''} — {dist_str}",
                })
            results.sort(key=lambda x: x["distance_m"])
            return results

        # Fallback: legacy Places Nearby Search
        async with httpx.AsyncClient(timeout=10.0) as client:
            r2 = await client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={
                    "query": f"{query} near me",
                    "location": f"{lat},{lng}",
                    "radius": radius,
                    "key": api_key,
                },
            )
            data2 = r2.json()

        results = []
        for p in data2.get("results", [])[:8]:
            loc = p.get("geometry", {}).get("location", {})
            p_lat, p_lng = loc.get("lat"), loc.get("lng")
            if not p_lat or not p_lng:
                continue
            dist = _haversine(lat, lng, p_lat, p_lng)
            dist_str = f"{round(dist / 1000, 1)} km" if dist >= 1000 else f"{dist} m"
            rating = p.get("rating", "")
            results.append({
                "name": p.get("name", "Unknown"),
                "lat": p_lat,
                "lng": p_lng,
                "distance_m": dist,
                "distance_str": dist_str,
                "address": p.get("vicinity", ""),
                "rating": rating,
                "open_now": p.get("opening_hours", {}).get("open_now"),
                "open_str": "",
                "phone": "",
                "display": f"{p.get('name', 'Unknown')}{f' ⭐{rating}' if rating else ''} — {dist_str}",
            })
        results.sort(key=lambda x: x["distance_m"])
        return results

    except Exception as e:
        print(f"[maps] find_nearby_places error: {e}")
        return [{"error": str(e)}]


@tool
async def get_route_and_traffic(
    user_id: str,
    destination_lat: float,
    destination_lng: float,
    destination_label: str = "destination",
    mode: str = "DRIVE",
) -> dict:
    """
    Get real-time traffic-aware route using Google Routes API.

    ALWAYS use this for travel time and directions questions:
    - "how long to get to work?"
    - "how do I get home from here?"
    - "directions to [place]"
    - "is there traffic on my way to work?"
    - "should I leave now or wait?"
    - "what's the fastest route to [destination]?"

    Args:
        user_id: The user's UUID
        destination_lat: Destination latitude
        destination_lng: Destination longitude
        destination_label: Human-readable destination name (e.g. "Work", "Home")
        mode: DRIVE, WALK, BICYCLE, TRANSIT
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "Google Maps not configured"}

    lat, lng = await _get_user_location(user_id)
    if not lat:
        return {"error": "Location not available"}

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.post(
                "https://routes.googleapis.com/directions/v2:computeRoutes",
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": (
                        "routes.duration,routes.distanceMeters,"
                        "routes.polyline,routes.staticDuration"
                    ),
                },
                json={
                    "origin": {
                        "location": {"latLng": {"latitude": lat, "longitude": lng}}
                    },
                    "destination": {
                        "location": {
                            "latLng": {
                                "latitude": destination_lat,
                                "longitude": destination_lng,
                            }
                        }
                    },
                    "travelMode": mode,
                    "routingPreference": "TRAFFIC_AWARE",
                    "departureTime": "now",
                    "computeAlternativeRoutes": False,
                    "languageCode": "en-US",
                    "units": "METRIC",
                },
            )
            data = r.json()

        if "routes" not in data or not data["routes"]:
            print(f"[maps] Routes API response: {data}")
            return {"error": "No route found"}

        route = data["routes"][0]

        duration_s = int(route.get("duration", "0s").rstrip("s"))
        static_s   = int(route.get("staticDuration", route.get("duration", "0s")).rstrip("s"))
        minutes_traffic    = int(duration_s / 60)
        minutes_no_traffic = int(static_s / 60)
        distance_m = route.get("distanceMeters", 0)
        km = round(distance_m / 1000, 1)

        delay = minutes_traffic - minutes_no_traffic
        if delay > 10:
            traffic_status = f"Heavy traffic — {delay} min delay"
        elif delay > 3:
            traffic_status = f"Moderate traffic — {delay} min delay"
        else:
            traffic_status = "Light traffic"

        if delay > 15:
            advice = (
                f"Traffic is bad right now — {minutes_traffic} min vs "
                f"{minutes_no_traffic} min without traffic. "
                f"Consider waiting 30-60 min or taking an alternate route."
            )
        elif delay > 5:
            advice = f"Some traffic on your route. Expect {minutes_traffic} min to {destination_label}."
        else:
            advice = f"Roads are fairly clear. About {minutes_traffic} min to {destination_label}."

        encoded = route.get("polyline", {}).get("encodedPolyline", "")
        waypoints = _decode_polyline(encoded) if encoded else [
            [lat, lng], [destination_lat, destination_lng]
        ]

        return {
            "duration_minutes": minutes_traffic,
            "duration_no_traffic_minutes": minutes_no_traffic,
            "traffic_delay_minutes": delay,
            "distance_km": km,
            "traffic_status": traffic_status,
            "advice": advice,
            "waypoints": waypoints,
            "origin": {"lat": lat, "lng": lng},
            "destination": {
                "lat": destination_lat,
                "lng": destination_lng,
                "label": destination_label,
            },
            "summary": f"{minutes_traffic} min with traffic ({km} km) — {traffic_status}",
        }

    except Exception as e:
        print(f"[maps] get_route_and_traffic error: {e}")
        return {"error": str(e)}


@tool
async def check_traffic_to_saved_location(
    user_id: str,
    location_type: str = "work",
) -> dict:
    """
    Check current traffic conditions to a saved location (home or work).

    CALL THIS for proactive traffic warnings and planning:
    - "how's traffic to work?"
    - "should I leave for work now?"
    - "is it a good time to head home?"
    - "traffic update"
    - "how long to get home?"
    - "am I going to be late?"

    Args:
        user_id: The user's UUID
        location_type: "home" or "work"
    """
    db = get_supabase()
    try:
        res = db.table("users")\
            .select("home_lat,home_lng,home_address,work_lat,work_lng,work_address")\
            .eq("id", user_id)\
            .maybe_single()\
            .execute()

        if not res.data:
            return {"error": "No saved locations found"}

        d = res.data
        if location_type == "work":
            dest_lat  = d.get("work_lat")
            dest_lng  = d.get("work_lng")
            dest_label = d.get("work_address") or "Work"
        else:
            dest_lat  = d.get("home_lat")
            dest_lng  = d.get("home_lng")
            dest_label = d.get("home_address") or "Home"

        if not dest_lat or not dest_lng:
            return {
                "error": (
                    f"No {location_type} location saved. "
                    f"Tell me your {location_type} address to save it."
                )
            }

        result = await get_route_and_traffic.ainvoke({
            "user_id": user_id,
            "destination_lat": dest_lat,
            "destination_lng": dest_lng,
            "destination_label": dest_label,
            "mode": "DRIVE",
        })
        result["destination_type"] = location_type
        return result

    except Exception as e:
        return {"error": str(e)}


@tool
async def search_place_by_name(
    user_id: str,
    place_name: str,
) -> dict:
    """
    Search for a specific place by name and get its coordinates.

    Use this when user mentions a specific place by name and wants
    directions to it or wants to know where it is:
    - "how do I get to Blenco Supermarket?"
    - "where is Duchess International Hospital?"
    - "find Wema Bank Marina branch"
    - directions to any named place

    After getting the result, pass the coordinates to get_route_and_traffic
    to give the user directions.

    Args:
        user_id: The user's UUID
        place_name: The exact or approximate name of the place
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "Google Maps not configured"}

    lat, lng = await _get_user_location(user_id)

    try:
        params: dict = {
            "query": f"{place_name} Lagos Nigeria",
            "key": api_key,
        }
        if lat:
            params["location"] = f"{lat},{lng}"
            params["radius"] = "50000"

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params=params,
            )
            data = r.json()

        results = data.get("results", [])
        if not results:
            return {"error": f"Could not find '{place_name}'"}

        p = results[0]
        loc = p.get("geometry", {}).get("location", {})
        p_lat = loc.get("lat")
        p_lng = loc.get("lng")

        dist = _haversine(lat, lng, p_lat, p_lng) if lat and p_lat else 0
        dist_str = f"{round(dist / 1000, 1)} km away" if dist >= 1000 else f"{dist} m away"

        return {
            "name": p.get("name"),
            "lat": p_lat,
            "lng": p_lng,
            "address": p.get("formatted_address", ""),
            "rating": p.get("rating", ""),
            "distance_str": dist_str,
            "distance_m": dist,
        }

    except Exception as e:
        return {"error": str(e)}
