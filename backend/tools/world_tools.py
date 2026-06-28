import httpx
from langchain_core.tools import tool
from backend.db.cache import cache_get
from backend.db.postgres import get_supabase
from datetime import datetime, timezone


@tool
async def get_world_state(user_id: str) -> dict:
    """Get the current world state for the user including location, weather, time, and context."""
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
    """Send a proactive nudge to the user. Priority: low, medium, or high."""
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
async def get_nearby_places(lat: float, lng: float, place_type: str = "restaurant", radius: int = 1500) -> list:
    """Find nearby places using Overpass API (OpenStreetMap) — completely free.
    place_type options: restaurant, cafe, pharmacy, atm, fuel, hospital, supermarket, bank, hotel
    """
    type_map = {
        "restaurant": ('amenity', 'restaurant'),
        "cafe": ('amenity', 'cafe'),
        "pharmacy": ('amenity', 'pharmacy'),
        "atm": ('amenity', 'atm'),
        "fuel": ('amenity', 'fuel'),
        "hospital": ('amenity', 'hospital'),
        "supermarket": ('shop', 'supermarket'),
        "bank": ('amenity', 'bank'),
        "hotel": ('tourism', 'hotel'),
        "guest_house": ('tourism', 'guest_house'),
    }
    tag_key, tag_val = type_map.get(place_type.lower(), ('amenity', place_type))

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
                print(f"Overpass error: status {r.status_code}")
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
        print(f"Overpass error: {e}")
        return []


@tool
async def get_travel_eta(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    mode: str = "driving",
) -> dict:
    """Get travel time and distance using OSRM — completely free.
    mode: driving, walking, cycling
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
            print(f"OSRM error: {e}")
        return {"error": "Route not available", "duration_minutes": None}
