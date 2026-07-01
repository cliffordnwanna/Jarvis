"""
JARVIS Maps Tools — powered by TomTom APIs (no billing required, real traffic data).
"""
import os
import math
import httpx
from langchain_core.tools import tool
from backend.db.cache import cache_get
from backend.db.postgres import get_supabase


def _haversine(lat1, lng1, lat2, lng2) -> int:
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return int(R * 2 * math.asin(math.sqrt(a)))


async def _get_user_location(user_id: str):
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
    Find any nearby place using TomTom Places Search API.

    ALWAYS use this when user asks to find ANYTHING nearby.
    The query accepts natural language — restaurant, church, suya spot,
    mechanic, pharmacy, Shoprite, ATM, hotel, fuel station, etc.

    Examples:
    - "find a restaurant near me"   → query="restaurant"
    - "find a church near me"       → query="church"
    - "find a Shoprite nearby"      → query="Shoprite"
    - "find somewhere to buy suya"  → query="suya"
    - "find a mechanic"             → query="mechanic"
    - "find an ATM"                 → query="ATM"
    - "find a pharmacy"             → query="pharmacy"

    Args:
        user_id: The user's UUID
        query: Natural language description of what to find
        radius: Search radius in meters (default 3000 = 3km)
    """
    api_key = os.getenv("TOMTOM_API_KEY")
    if not api_key:
        return [{"error": "TomTom API key not configured"}]

    lat, lng = await _get_user_location(user_id)
    if not lat:
        return [{"error": "Location not available"}]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # POI search — best for typed places (restaurant, ATM, etc.)
            r = await client.get(
                f"https://api.tomtom.com/search/2/poiSearch/{query}.json",
                params={
                    "key": api_key,
                    "lat": lat,
                    "lon": lng,
                    "radius": radius,
                    "limit": 8,
                    "language": "en-GB",
                    "countrySet": "NG",
                },
            )
            data = r.json()
            raw = data.get("results", [])

            # Fallback: fuzzy search (handles brand names, custom queries)
            if not raw:
                r2 = await client.get(
                    f"https://api.tomtom.com/search/2/search/{query}.json",
                    params={
                        "key": api_key,
                        "lat": lat,
                        "lon": lng,
                        "radius": radius,
                        "limit": 8,
                        "language": "en-GB",
                        "countrySet": "NG",
                    },
                )
                raw = r2.json().get("results", [])

        results = []
        for item in raw:
            pos = item.get("position", {})
            p_lat = pos.get("lat")
            p_lng = pos.get("lon")
            if not p_lat or not p_lng:
                continue
            dist = item.get("dist") or _haversine(lat, lng, p_lat, p_lng)
            dist_str = f"{round(dist / 1000, 1)} km" if dist >= 1000 else f"{int(dist)} m"
            poi = item.get("poi", {})
            address = item.get("address", {})
            name = poi.get("name") or address.get("freeformAddress", "Unknown")
            results.append({
                "name": name,
                "lat": p_lat,
                "lng": p_lng,
                "distance_m": int(dist),
                "distance_str": dist_str,
                "address": address.get("freeformAddress", ""),
                "phone": poi.get("phone", ""),
                "category": (poi.get("categories") or [""])[0],
                "display": f"{name} — {dist_str}",
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
    mode: str = "car",
) -> dict:
    """
    Get real-time traffic-aware route using TomTom Routing API.

    ALWAYS use this for travel time and directions questions:
    - "how long to get to work?"
    - "how do I get home from here?"
    - "directions to [place]"
    - "is there traffic on my way?"
    - "should I leave now or wait?"

    Args:
        user_id: The user's UUID
        destination_lat: Destination latitude
        destination_lng: Destination longitude
        destination_label: Human-readable destination name (e.g. "Work", "Home")
        mode: car, pedestrian, bicycle, motorcycle
    """
    api_key = os.getenv("TOMTOM_API_KEY")
    if not api_key:
        return {"error": "TomTom API key not configured"}

    lat, lng = await _get_user_location(user_id)
    if not lat:
        return {"error": "Location not available"}

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(
                f"https://api.tomtom.com/routing/1/calculateRoute/"
                f"{lat},{lng}:{destination_lat},{destination_lng}/json",
                params={
                    "key": api_key,
                    "travelMode": mode,
                    "traffic": "true",
                    "routeType": "fastest",
                    "computeTravelTimeFor": "all",
                },
            )
            if r.status_code != 200:
                print(f"[maps] TomTom routing HTTP {r.status_code}: {r.text[:200]}")
                return {"error": "Route not available", "duration_minutes": None}
            data = r.json()

        routes = data.get("routes", [])
        if not routes:
            return {"error": "No route found", "duration_minutes": None}

        summary = routes[0].get("summary", {})
        duration_s          = summary.get("travelTimeInSeconds", 0)
        duration_no_traffic = summary.get("noTrafficTravelTimeInSeconds", duration_s)
        distance_m          = summary.get("lengthInMeters", 0)

        minutes            = int(duration_s / 60)
        minutes_no_traffic = int(duration_no_traffic / 60)
        km                 = round(distance_m / 1000, 1)
        delay              = minutes - minutes_no_traffic

        if delay > 15:
            traffic_status = f"Heavy traffic — {delay} min delay"
            advice = (
                f"Traffic is bad right now — {minutes} min vs {minutes_no_traffic} min without traffic. "
                f"Consider waiting 30-60 min or leaving now if you can't wait."
            )
        elif delay > 5:
            traffic_status = f"Moderate traffic — {delay} min delay"
            advice = f"Some traffic on your route. Expect {minutes} min to {destination_label}."
        else:
            traffic_status = "Light traffic"
            advice = f"Roads are clear. About {minutes} min to {destination_label}."

        # Extract waypoints from route leg points
        waypoints = []
        for leg in routes[0].get("legs", []):
            for pt in leg.get("points", []):
                waypoints.append([pt["latitude"], pt["longitude"]])

        # Downsample to 100 points max for map performance
        if len(waypoints) > 100:
            step = max(1, len(waypoints) // 100)
            waypoints = waypoints[::step]
            # Always keep destination
            if waypoints[-1] != [destination_lat, destination_lng]:
                waypoints.append([destination_lat, destination_lng])

        if not waypoints:
            waypoints = [[lat, lng], [destination_lat, destination_lng]]

        return {
            "duration_minutes": minutes,
            "duration_no_traffic_minutes": minutes_no_traffic,
            "traffic_delay_minutes": delay,
            "distance_km": km,
            "traffic_status": traffic_status,
            "advice": advice,
            "waypoints": waypoints,
            "origin": {"lat": lat, "lng": lng},
            "destination": {"lat": destination_lat, "lng": destination_lng, "label": destination_label},
            "summary": f"{minutes} min with traffic ({km} km) — {traffic_status}",
        }

    except Exception as e:
        print(f"[maps] get_route_and_traffic error: {e}")
        return {"error": str(e), "duration_minutes": None}


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
            dest_lat   = d.get("work_lat")
            dest_lng   = d.get("work_lng")
            dest_label = d.get("work_address") or "Work"
        else:
            dest_lat   = d.get("home_lat")
            dest_lng   = d.get("home_lng")
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
            "mode": "car",
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
    Search for a specific named place and get its coordinates.

    Use when user mentions a specific place by name and wants
    directions to it or wants to know where it is:
    - "how do I get to Blenco Supermarket?"
    - "where is Duchess International Hospital?"
    - "find Wema Bank Marina branch"

    After getting coordinates, pass them to get_route_and_traffic
    to give the user directions.

    Args:
        user_id: The user's UUID
        place_name: The name of the place to find
    """
    api_key = os.getenv("TOMTOM_API_KEY")
    if not api_key:
        return {"error": "TomTom API key not configured"}

    lat, lng = await _get_user_location(user_id)

    try:
        params: dict = {
            "key": api_key,
            "limit": 1,
            "countrySet": "NG",
            "language": "en-GB",
        }
        if lat:
            params["lat"] = lat
            params["lon"] = lng
            params["radius"] = 50000

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"https://api.tomtom.com/search/2/search/{place_name} Lagos.json",
                params=params,
            )
            data = r.json()

        results = data.get("results", [])
        if not results:
            return {"error": f"Could not find '{place_name}'"}

        p = results[0]
        pos = p.get("position", {})
        p_lat = pos.get("lat")
        p_lng = pos.get("lon")
        dist = p.get("dist") or (_haversine(lat, lng, p_lat, p_lng) if lat and p_lat else 0)
        dist_str = f"{round(dist / 1000, 1)} km away" if dist >= 1000 else f"{int(dist)} m away"

        poi = p.get("poi", {})
        address = p.get("address", {})

        return {
            "name": poi.get("name") or place_name,
            "lat": p_lat,
            "lng": p_lng,
            "address": address.get("freeformAddress", ""),
            "distance_str": dist_str,
            "distance_m": int(dist),
            "phone": poi.get("phone", ""),
        }

    except Exception as e:
        return {"error": str(e)}
