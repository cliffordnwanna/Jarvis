"""
JARVIS v2 — World State Builder
================================
Assembles the complete world-state object from free APIs.
Every LLM call receives this object. This is the product.

APIs used (all free, no cost):
  - Open-Meteo          → weather + air quality (no key, unlimited)
  - Nominatim OSM       → geocoding coords→city (no key, 1 req/s)
  - Sunrise-Sunset.org  → sunrise/sunset times (no key, unlimited)
  - WorldTimeAPI        → timezone + week info (no key, unlimited)
  - Nager.Date          → public holidays (no key, unlimited)
  - Overpass API (OSM)  → nearby places (no key, unlimited)
  - TomTom Traffic      → congestion + ETA (free key, 2500/day)
  - Google Calendar API → events (OAuth, free quota)
  - Browser APIs        → battery, network, GPS (client-side only)

Architecture: Event-driven, not polling.
  Triggers: location_changed, calendar_update, weather_shifted,
            battery_threshold, time_window, user_activity
"""

import asyncio
import math
import httpx
from datetime import datetime, date
from typing import Optional
from zoneinfo import ZoneInfo


# ─── CONFIG ──────────────────────────────────────────────────────────────────

TOMTOM_API_KEY = "YOUR_FREE_TOMTOM_KEY"   # free at developer.tomtom.com
GOOGLE_CALENDAR_TOKEN = "YOUR_OAUTH_TOKEN" # from Google OAuth flow

NOMINATIM_HEADERS = {
    "User-Agent": "JARVIS-Personal-AI/2.0 (your@email.com)"  # required by OSM policy
}


# ─── LAYER 1: TEMPORAL ────────────────────────────────────────────────────────

async def fetch_temporal(lat: float, lng: float, hint_timezone: str | None = None) -> dict:
    """
    Sources: WorldTimeAPI (week number only), Sunrise-Sunset.org, Nager.Date, math (moon phase)
    hint_timezone: IANA timezone string sent by the browser (e.g. "Africa/Lagos").
    When provided it overrides the IP-based timezone from WorldTimeAPI, which is
    unreliable on VPNs and always wrong when the server runs on localhost.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:

        # WorldTimeAPI — only used for week_number; timezone is overridden by hint
        week_number = datetime.now().isocalendar()[1]
        try:
            tz_resp = await client.get("http://worldtimeapi.org/api/ip")
            tz_data = tz_resp.json()
            week_number = tz_data.get("week_number", week_number)
            # Fall back to API timezone only when no hint was provided
            if not hint_timezone:
                hint_timezone = tz_data.get("timezone") or None
        except Exception:
            pass

        timezone = hint_timezone or "UTC"

        # Compute UTC offset from the actual IANA zone — never from the API string
        try:
            tz_obj = ZoneInfo(timezone)
            _now_for_offset = datetime.now(tz_obj)
            _offset_s = int(_now_for_offset.utcoffset().total_seconds())
            _sign = "+" if _offset_s >= 0 else "-"
            _h, _r = divmod(abs(_offset_s), 3600)
            utc_offset = f"{_sign}{_h:02d}:{_r // 60:02d}"
        except Exception:
            utc_offset = "+00:00"

        # Current time in user's timezone
        try:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
        except Exception:
            now = datetime.now()

        # Sunrise-Sunset.org — free, no key, no limits
        sunrise = sunset = None
        try:
            sun_resp = await client.get(
                "https://api.sunrise-sunset.org/json",
                params={"lat": lat, "lng": lng, "formatted": 0, "date": "today"}
            )
            sun_data = sun_resp.json().get("results", {})
            # API returns UTC times — convert to local
            sunrise_utc = datetime.fromisoformat(sun_data.get("sunrise", ""))
            sunset_utc = datetime.fromisoformat(sun_data.get("sunset", ""))
            sunrise = sunrise_utc.astimezone(ZoneInfo(timezone)).strftime("%H:%M")
            sunset = sunset_utc.astimezone(ZoneInfo(timezone)).strftime("%H:%M")
        except Exception:
            pass

        # Nager.Date — public holidays by country code
        is_public_holiday = False
        holiday_name = None
        try:
            # Country code resolved later from geocoding; default NG
            country_code = "NG"
            holiday_resp = await client.get(
                f"https://date.nager.at/api/v3/PublicHolidays/{now.year}/{country_code}"
            )
            holidays = holiday_resp.json()
            today_str = now.strftime("%Y-%m-%d")
            for h in holidays:
                if h.get("date") == today_str:
                    is_public_holiday = True
                    holiday_name = h.get("name")
                    break
        except Exception:
            pass

        # Time of day classification
        hour = now.hour
        if 5 <= hour < 8:
            time_of_day = "dawn"
        elif 8 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 14:
            time_of_day = "midday"
        elif 14 <= hour < 18:
            time_of_day = "afternoon"
        elif 18 <= hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "night"

        # Moon phase — calculated mathematically, no API needed
        moon_phase = _calculate_moon_phase(now.date())

        return {
            "timestamp": now.isoformat(),
            "timezone": timezone,
            "utc_offset": utc_offset,
            "day_of_week": now.strftime("%A"),
            "day_number": now.weekday(),       # 0=Monday, 6=Sunday
            "week_number": week_number,
            "month": now.month,
            "year": now.year,
            "hour_decimal": hour + now.minute / 60,
            "is_weekend": now.weekday() >= 5,
            "is_public_holiday": is_public_holiday,
            "holiday_name": holiday_name,
            "time_of_day": time_of_day,
            "sunrise": sunrise,
            "sunset": sunset,
            "is_daylight": _is_daylight(now, sunrise, sunset),
            "moon_phase": moon_phase,
            "minutes_until_midnight": (23 - hour) * 60 + (59 - now.minute),
        }


def _calculate_moon_phase(d: date) -> str:
    """Calculate moon phase from date — no API needed."""
    diff = (d - date(2001, 1, 1)).days
    cycle = diff % 29.53
    if cycle < 1.85: return "new_moon"
    elif cycle < 7.38: return "waxing_crescent"
    elif cycle < 9.22: return "first_quarter"
    elif cycle < 14.77: return "waxing_gibbous"
    elif cycle < 16.61: return "full_moon"
    elif cycle < 22.15: return "waning_gibbous"
    elif cycle < 23.99: return "last_quarter"
    else: return "waning_crescent"


def _is_daylight(now: datetime, sunrise: Optional[str], sunset: Optional[str]) -> bool:
    if not sunrise or not sunset:
        return 6 <= now.hour < 18  # fallback
    try:
        h, m = map(int, sunrise.split(":"))
        sr_min = h * 60 + m
        h, m = map(int, sunset.split(":"))
        ss_min = h * 60 + m
        cur_min = now.hour * 60 + now.minute
        return sr_min <= cur_min <= ss_min
    except Exception:
        return 6 <= now.hour < 18


# ─── LAYER 2: LOCATION ────────────────────────────────────────────────────────

async def fetch_location(lat: float, lng: float) -> dict:
    """
    Sources: Nominatim OSM (geocoding), ip-api.com (IP fallback)
    Trigger: on GPS coordinates change (>100m)
    Note: Nominatim requires 1 req/s max — always cache results
    """
    city = district = state = country = country_code = "Unknown"

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lng, "format": "json"},
                headers=NOMINATIM_HEADERS
            )
            data = resp.json()
            addr = data.get("address", {})
            # Extended fallback chain — covers Nigeria and other regions where
            # Nominatim uses state/county/suburb instead of city/town/village
            city = (
                addr.get("city") or
                addr.get("town") or
                addr.get("village") or
                addr.get("municipality") or
                addr.get("city_district") or
                addr.get("suburb") or
                addr.get("county") or
                addr.get("state_district") or
                addr.get("state") or
                "Unknown"
            )
            district = (
                addr.get("suburb") or
                addr.get("neighbourhood") or
                addr.get("district") or
                addr.get("city_district") or
                ""
            )
            state = (
                addr.get("state") or
                addr.get("state_district") or
                addr.get("county") or
                ""
            )
            country = addr.get("country", "Unknown")
            country_code = addr.get("country_code", "").upper()
        except Exception:
            # Fallback: IP-based geolocation
            try:
                ip_resp = await client.get("http://ip-api.com/json")
                ip_data = ip_resp.json()
                city = ip_data.get("city", "Unknown")
                state = ip_data.get("regionName", "")
                country = ip_data.get("country", "Unknown")
                country_code = ip_data.get("countryCode", "")
            except Exception:
                pass

    return {
        "lat": lat,
        "lng": lng,
        "city": city,
        "state": state,
        "district": district,
        "country": country,
        "country_code": country_code,
        # These are enriched by the learning layer over time:
        "location_type": "unknown",        # → "home"/"work"/"gym" after learning
        "location_label": None,            # → "Wema Bank Office" after learning
        "duration_here_minutes": None,     # → tracked in Redis
        "movement_state": "unknown",       # → "stationary"/"walking"/"driving"
        "speed_kmh": 0,
    }


# ─── LAYER 3: TRAJECTORY (derived from location history) ─────────────────────

def build_trajectory(location_history: list[dict]) -> dict:
    """
    Derived from PostgreSQL location history — no external API.
    Trigger: whenever location updates.
    """
    if len(location_history) < 2:
        return {
            "came_from": None,
            "time_left_previous": None,
            "commute_complete": False,
            "probable_next_location": None,
            "movement_intent": "unknown",
            "trajectory_confidence": 0.0,
        }

    prev = location_history[-2]
    curr = location_history[-1]

    return {
        "came_from": prev.get("location_label") or prev.get("city"),
        "time_left_previous": prev.get("left_at"),
        "commute_complete": (
            curr.get("location_type") == "home" and
            prev.get("location_type") == "work"
        ),
        "probable_next_location": "sleep",   # enriched by pattern learning
        "movement_intent": "settled" if curr.get("movement_state") == "stationary" else "commuting",
        "usual_departure_time": None,         # → populated from pattern DB
        "trajectory_confidence": 0.88,
    }


# ─── LAYER 4: ENVIRONMENT ─────────────────────────────────────────────────────

async def fetch_environment(lat: float, lng: float) -> dict:
    """
    Sources: Open-Meteo (weather + air quality) — completely free, no key, no limits
    Trigger: every 30 minutes OR when weather_code changes significantly
    """
    weather = {}
    air_quality = {}

    async with httpx.AsyncClient(timeout=8.0) as client:

        # Open-Meteo weather — includes forecast
        try:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lng,
                    "current": [
                        "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                        "weather_code", "wind_speed_10m", "wind_direction_10m",
                        "precipitation", "cloud_cover", "uv_index", "is_day"
                    ],
                    "hourly": ["precipitation_probability", "temperature_2m"],
                    "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min",
                              "precipitation_probability_max"],
                    "timezone": "auto",
                    "forecast_days": 2,
                }
            )
            data = resp.json()
            curr = data.get("current", {})
            hourly = data.get("hourly", {})
            daily = data.get("daily", {})

            rain_probs = hourly.get("precipitation_probability", [0] * 24)

            weather = {
                "condition": _wmo_to_condition(curr.get("weather_code", 0)),
                "description": _wmo_to_description(curr.get("weather_code", 0)),
                "temp_c": curr.get("temperature_2m"),
                "feels_like_c": curr.get("apparent_temperature"),
                "humidity_pct": curr.get("relative_humidity_2m"),
                "wind_speed_kmh": curr.get("wind_speed_10m"),
                "wind_direction": _degrees_to_compass(curr.get("wind_direction_10m", 0)),
                "cloud_cover_pct": curr.get("cloud_cover"),
                "uv_index": curr.get("uv_index"),
                "precipitation_mm": curr.get("precipitation"),
                "is_day": bool(curr.get("is_day")),
                "forecast_1h_rain_prob": rain_probs[1] / 100 if len(rain_probs) > 1 else 0,
                "forecast_3h_rain_prob": max(rain_probs[1:4]) / 100 if len(rain_probs) > 3 else 0,
                "tomorrow_max_c": daily.get("temperature_2m_max", [None, None])[1],
                "tomorrow_min_c": daily.get("temperature_2m_min", [None, None])[1],
                "tomorrow_rain_prob": (daily.get("precipitation_probability_max", [0, 0])[1] or 0) / 100,
                "tomorrow_condition": _wmo_to_condition(
                    (daily.get("weather_code", [0, 0]) or [0, 0])[1]
                ),
            }
        except Exception as e:
            weather = {"error": str(e)}

        # Open-Meteo Air Quality — also free, no key
        try:
            aq_resp = await client.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={
                    "latitude": lat,
                    "longitude": lng,
                    "current": ["pm2_5", "pm10", "european_aqi", "us_aqi"],
                }
            )
            aq_data = aq_resp.json().get("current", {})
            aqi = aq_data.get("european_aqi") or aq_data.get("us_aqi", 0)
            air_quality = {
                "aqi": aqi,
                "category": _aqi_category(aqi),
                "pm25": aq_data.get("pm2_5"),
                "pm10": aq_data.get("pm10"),
            }
        except Exception:
            air_quality = {"aqi": None, "category": "unknown"}

    return {"weather": weather, "air_quality": air_quality}


def _wmo_to_condition(code: int) -> str:
    """Convert WMO weather code to readable condition."""
    if code == 0: return "clear"
    elif code in (1, 2, 3): return "partly_cloudy"
    elif code in (45, 48): return "foggy"
    elif code in (51, 53, 55): return "drizzle"
    elif code in (61, 63, 65): return "rain"
    elif code in (71, 73, 75): return "snow"
    elif code in (80, 81, 82): return "rain_showers"
    elif code in (95, 96, 99): return "thunderstorm"
    else: return "unknown"


def _wmo_to_description(code: int) -> str:
    descriptions = {
        0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
        45: "foggy", 48: "icy fog", 51: "light drizzle", 53: "drizzle",
        55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
        71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
        81: "moderate showers", 82: "violent showers", 95: "thunderstorm",
        96: "thunderstorm with hail", 99: "thunderstorm with heavy hail"
    }
    return descriptions.get(code, "unknown")


def _degrees_to_compass(deg: float) -> str:
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[round(deg / 45) % 8]


def _aqi_category(aqi: Optional[int]) -> str:
    if aqi is None: return "unknown"
    if aqi <= 50: return "good"
    elif aqi <= 100: return "moderate"
    elif aqi <= 150: return "unhealthy_sensitive"
    elif aqi <= 200: return "unhealthy"
    elif aqi <= 300: return "very_unhealthy"
    else: return "hazardous"


# ─── LAYER 5: DEVICE (client-side — sent from PWA frontend) ──────────────────

def build_device_context(client_payload: dict) -> dict:
    """
    Sources: Browser Battery Status API, Network Information API
    These are sent from the PWA frontend to the backend.
    Trigger: on battery level change, network change
    """
    battery_pct = client_payload.get("battery_pct", 100)
    charging = client_payload.get("charging", False)

    # Infer preferred interaction modality
    headphones = client_payload.get("headphones_connected", False)
    battery_low = battery_pct < 20
    preferred_modality = "voice" if headphones else "text"

    return {
        "battery_pct": battery_pct,
        "charging": charging,
        "battery_state": "charging" if charging else "discharging",
        "battery_low": battery_low,
        "estimated_battery_life_minutes": _estimate_battery_life(battery_pct, charging),
        "network_type": client_payload.get("network_type", "unknown"),
        "network_quality": client_payload.get("network_quality", "unknown"),
        "effective_type": client_payload.get("effective_type", "4g"),
        "screen_on": client_payload.get("screen_on", True),
        "platform": client_payload.get("platform", "web"),
        "headphones_connected": headphones,
        "preferred_modality": preferred_modality,
    }


def _estimate_battery_life(pct: int, charging: bool) -> Optional[int]:
    if charging:
        return None
    # Rough estimate: typical smartphone drains ~10% per hour active
    return (pct / 10) * 60


# ─── LAYER 6: CALENDAR (Google Calendar API) ─────────────────────────────────

async def fetch_calendar(timezone: str = "UTC") -> dict:
    """
    Source: Google Calendar API (free with OAuth)
    Trigger: on calendar event create/update, or every 15 min
    """
    # In production: use google-auth-oauthlib + googleapiclient
    # Placeholder showing the structure
    events_today = []
    events_tomorrow = []

    # Derive cognitive load from meetings
    meeting_fatigue = _calculate_meeting_fatigue(events_today)

    now = datetime.now(ZoneInfo(timezone))

    upcoming = [e for e in events_today if _event_time(e) > now]
    completed = [e for e in events_today if _event_time(e) <= now]

    next_event = upcoming[0] if upcoming else None
    next_tomorrow = events_tomorrow[0] if events_tomorrow else None

    return {
        "events_today_total": len(events_today),
        "events_remaining": len(upcoming),
        "events_completed": len(completed),
        "meeting_load": _meeting_load_label(len(events_today)),
        "meeting_fatigue_score": meeting_fatigue,
        "has_back_to_back": _has_back_to_back(events_today),
        "next_event": _format_event(next_event, now) if next_event else None,
        "next_event_tomorrow": _format_event(next_tomorrow, now) if next_tomorrow else None,
        "free_blocks_today": _find_free_blocks(events_today, now),
        "in_meeting_now": _is_in_meeting(events_today, now),
    }


def _calculate_meeting_fatigue(events: list) -> float:
    """More meetings + back-to-back = higher fatigue score (0-1)."""
    base = min(len(events) / 8, 1.0)
    back_to_back_penalty = 0.2 if _has_back_to_back(events) else 0
    return min(base + back_to_back_penalty, 1.0)


def _meeting_load_label(count: int) -> str:
    if count == 0: return "free"
    elif count <= 2: return "light"
    elif count <= 4: return "moderate"
    else: return "heavy"


def _has_back_to_back(events: list) -> bool:
    # Check if any two events overlap or have <15 min gap
    return False  # implement with actual event times


def _event_time(event: dict) -> datetime:
    return datetime.now()  # implement with actual event parsing


def _format_event(event: dict, now: datetime) -> Optional[dict]:
    if not event:
        return None
    event_time = _event_time(event)
    delta = event_time - now
    return {
        "title": event.get("summary", "Meeting"),
        "time": event_time.strftime("%H:%M"),
        "in_minutes": int(delta.total_seconds() / 60),
        "location": event.get("location"),
        "is_virtual": "meet.google" in (event.get("location") or ""),
    }


def _find_free_blocks(events: list, now: datetime) -> list:
    return []  # implement gap detection between events


def _is_in_meeting(events: list, now: datetime) -> bool:
    return False  # implement overlap check


# ─── LAYER 7: TRAFFIC (TomTom free tier) ─────────────────────────────────────

async def fetch_traffic(
    lat: float, lng: float,
    home_lat: float = None, home_lng: float = None,
    work_lat: float = None, work_lng: float = None,
) -> dict:
    """
    Source: TomTom Traffic API (free key, 2500 req/day)
    Trigger: only in pre-commute windows (7-9am, 4-7pm)
    """
    if not TOMTOM_API_KEY or TOMTOM_API_KEY == "YOUR_FREE_TOMTOM_KEY":
        return {"available": False, "reason": "no_api_key"}

    congestion = "unknown"
    delay = 0

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(
                f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
                params={"key": TOMTOM_API_KEY, "point": f"{lat},{lng}"}
            )
            data = resp.json().get("flowSegmentData", {})
            current_speed = data.get("currentSpeed", 0)
            free_flow_speed = data.get("freeFlowSpeed", 1)

            ratio = current_speed / max(free_flow_speed, 1)
            if ratio > 0.8: congestion = "low"
            elif ratio > 0.5: congestion = "moderate"
            elif ratio > 0.25: congestion = "heavy"
            else: congestion = "severe"

            delay = max(0, int((1 - ratio) * 30))  # rough delay estimate

        except Exception:
            pass

    return {
        "available": True,
        "current_congestion": congestion,
        "delay_minutes": delay,
        "home_to_work_eta_now": None,      # from routing API call
        "usual_eta_minutes": None,          # from learned patterns
        "incidents_on_route": 0,
        "best_departure_window": None,      # derived from forecast
    }


# ─── LAYER 8: NEARBY (Overpass API — OpenStreetMap) ──────────────────────────

async def fetch_nearby(lat: float, lng: float, radius_m: int = 1000) -> dict:
    """
    Source: Overpass API (OpenStreetMap) — completely free, no API key
    Trigger: on location change (>200m)
    """
    query = f"""
    [out:json][timeout:10];
    (
      node["amenity"="restaurant"](around:{radius_m},{lat},{lng});
      node["amenity"="cafe"](around:{radius_m},{lat},{lng});
      node["amenity"="fast_food"](around:{radius_m},{lat},{lng});
      node["amenity"="pharmacy"](around:{radius_m},{lat},{lng});
      node["leisure"="fitness_centre"](around:{radius_m},{lat},{lng});
      node["amenity"="fuel"](around:{radius_m},{lat},{lng});
      node["amenity"="hospital"](around:{radius_m},{lat},{lng});
    );
    out body;
    """
    results = {
        "restaurants": [],
        "cafes": [],
        "pharmacies": [],
        "gyms": [],
        "petrol_stations": [],
        "hospitals": [],
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query}
            )
            elements = resp.json().get("elements", [])

            for el in elements:
                tags = el.get("tags", {})
                amenity = tags.get("amenity")
                name = tags.get("name", "Unnamed")
                el_lat = el.get("lat", lat)
                el_lng = el.get("lon", lng)
                dist = _haversine_distance(lat, lng, el_lat, el_lng)

                item = {"name": name, "distance_m": int(dist), "tags": tags}

                if amenity in ("restaurant", "fast_food"):
                    results["restaurants"].append(item)
                elif amenity == "cafe":
                    results["cafes"].append(item)
                elif amenity == "pharmacy":
                    results["pharmacies"].append(item)
                elif amenity == "fuel":
                    results["petrol_stations"].append(item)
                elif amenity == "hospital":
                    results["hospitals"].append(item)
                elif tags.get("leisure") == "fitness_centre":
                    results["gyms"].append(item)

            # Sort by distance
            for key in results:
                results[key].sort(key=lambda x: x["distance_m"])

        except Exception:
            pass

    # Summary stats
    return {
        "restaurants_open_count": len(results["restaurants"]),
        "nearest_restaurant": results["restaurants"][0] if results["restaurants"] else None,
        "pharmacy_available": len(results["pharmacies"]) > 0,
        "nearest_pharmacy": results["pharmacies"][0] if results["pharmacies"] else None,
        "gym_available": len(results["gyms"]) > 0,
        "petrol_available": len(results["petrol_stations"]) > 0,
        "hospital_nearby": len(results["hospitals"]) > 0,
        "raw": results,  # full list available for generative UI
    }


def _haversine_distance(lat1, lng1, lat2, lng2) -> float:
    """Distance in metres between two GPS coordinates."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# ─── LAYERS 9-10: COGNITIVE + BIOLOGICAL (fully derived) ─────────────────────

def derive_cognitive_state(calendar: dict, temporal: dict, behavioral: dict) -> dict:
    """
    Derived from: calendar load, time of day, learned patterns.
    No external API. This is pure inference.
    """
    hour = temporal.get("hour_decimal", 12)
    meeting_fatigue = calendar.get("meeting_fatigue_score", 0)
    in_meeting = calendar.get("in_meeting_now", False)

    # Focus degrades throughout the day, recovers after rest
    base_focus = 1.0 - (hour - 9) / 16 if hour >= 9 else 0.5
    focus = max(0, min(1, base_focus - meeting_fatigue * 0.4))

    fatigue = min(1, meeting_fatigue + (hour - 9) / 24 if hour >= 9 else 0.2)
    overload = min(1, (meeting_fatigue + (1 - focus)) / 2)

    # Interrupt sensitivity: high when in meeting, tired, or focused
    interrupt_sensitivity = max(in_meeting * 0.9, fatigue * 0.6, focus * 0.5)

    return {
        "estimated_focus": round(focus, 2),
        "estimated_fatigue": round(fatigue, 2),
        "estimated_overload": round(overload, 2),
        "in_meeting": in_meeting,
        "deep_work_likely": focus > 0.7 and not in_meeting,
        "interruption_sensitivity": round(interrupt_sensitivity, 2),
        "preferred_modality": "voice" if hour > 21 else "text",
        "preferred_response_length": "short" if fatigue > 0.6 else "medium",
    }


def derive_biological_signals(temporal: dict, behavioral: dict) -> dict:
    """
    Derived from time patterns + learned user habits.
    hunger_probability rises the longer since the last logged meal.
    """
    hour = temporal.get("hour_decimal", 12)
    hours_since_meal = behavioral.get("hours_since_last_meal", 0)

    # Hunger model: rises after 3h, peaks at 6h
    hunger = min(1.0, max(0, (hours_since_meal - 3) / 3))

    # Sleep pressure: rises after typical bedtime
    typical_sleep = behavioral.get("typical_sleep_hour", 1.0)  # 1am default
    adjusted_hour = hour if hour > 12 else hour + 24
    typical_adjusted = typical_sleep if typical_sleep > 12 else typical_sleep + 24
    sleep_pressure = min(1.0, max(0, (adjusted_hour - typical_adjusted + 2) / 3))

    energy = max(0, 1 - (sleep_pressure * 0.5 + hour / 24 * 0.3))

    return {
        "hunger_probability": round(hunger, 2),
        "hours_since_last_meal": hours_since_meal,
        "thirst_probability": round(min(1.0, hours_since_meal / 8), 2),
        "sleep_pressure": round(sleep_pressure, 2),
        "estimated_energy": round(energy, 2),
        "sleep_debt_likely": behavioral.get("avg_sleep_hours", 7) < 6.5,
        "typical_sleep_time": behavioral.get("typical_sleep_time", "01:00"),
        "minutes_until_bedtime": _minutes_until(temporal, typical_sleep),
    }


def _minutes_until(temporal: dict, target_hour: float) -> int:
    current = temporal.get("hour_decimal", 0)
    if target_hour < current:
        target_hour += 24
    return int((target_hour - current) * 60)


# ─── LAYER 11: GOALS (PostgreSQL memory) ─────────────────────────────────────

def load_goals(db_goals: list[dict]) -> dict:
    """
    Source: PostgreSQL — populated from conversations and explicit user input.
    This layer grows richer over time without any API calls.
    """
    active = [g for g in db_goals if g.get("status") == "active"]
    stale = [g for g in active if g.get("days_since_touched", 0) > 3]
    high_urgency = [g for g in active if g.get("urgency") == "high"]

    return {
        "active_goals": active,
        "stale_goals": stale,
        "stale_count": len(stale),
        "high_urgency_count": len(high_urgency),
        "completed_today": [g for g in db_goals if g.get("completed_today")],
        "blocked_count": len([g for g in active if g.get("status") == "blocked"]),
    }


# ─── LAYER 12: INFERRED INTENT (LLM synthesis) ───────────────────────────────

async def infer_intent(world_state: dict, llm_client) -> dict:
    """
    The synthesis layer. Aggregates all 11 layers into actionable intelligence.
    Uses Groq (fast, cheap) for simple classification.
    Uses Claude for complex multi-signal synthesis.
    """
    prompt = f"""
You are the JARVIS world-state inference engine.

Given this complete world state, determine:
1. probable_current_activity: one of [working, commuting, eating, exercising, socializing, winding_down, sleeping, unknown]
2. likely_needs: list of up to 3 items from [food, water, rest, movement, focus, social, reminder, navigation]
3. nudge_type: one of [none, gentle, standard, urgent]
4. nudge_delivery: one of [none, voice, sidebar_card, push_notification]
5. interrupt_score: float 0-1 (1 = definitely interrupt)
6. context_summary: one sentence summarizing the user's current situation for LLM context injection

Respond in JSON only. No explanation.

World state:
{world_state}
"""
    # In production: call Groq here (fast + free tier available)
    # response = await groq_client.chat.completions.create(...)
    # For now, return a placeholder
    return {
        "probable_activity": "winding_down",
        "likely_needs": ["food", "rest"],
        "nudge_type": "gentle",
        "nudge_delivery": "sidebar_card",
        "interrupt_score": 0.38,
        "context_summary": (
            f"Late evening. Heavy day. Hungry and winding down. "
            f"ACS application stale. Next commitment tomorrow at 09:00."
        )
    }


# ─── MASTER BUILDER ───────────────────────────────────────────────────────────

async def build_world_state(
    lat: float,
    lng: float,
    device_payload: dict,
    location_history: list[dict],
    behavioral: dict,
    db_goals: list[dict],
    llm_client=None,
) -> dict:
    """
    Main entry point. Assembles the complete world state from all layers.
    Called event-driven (on location change, calendar update, etc.)
    Returns the object injected into every LLM call.
    """

    # Fetch all external data in parallel
    temporal, location, environment, calendar, traffic, nearby = await asyncio.gather(
        fetch_temporal(lat, lng, hint_timezone=behavioral.get("timezone")),
        fetch_location(lat, lng),
        fetch_environment(lat, lng),
        fetch_calendar(timezone=behavioral.get("timezone", "UTC")),
        fetch_traffic(lat, lng),
        fetch_nearby(lat, lng),
        return_exceptions=True,
    )

    # Handle any failed fetches gracefully
    temporal = temporal if not isinstance(temporal, Exception) else {}
    location = location if not isinstance(location, Exception) else {}
    environment = environment if not isinstance(environment, Exception) else {}
    calendar = calendar if not isinstance(calendar, Exception) else {}
    traffic = traffic if not isinstance(traffic, Exception) else {}
    nearby = nearby if not isinstance(nearby, Exception) else {}

    # Build derived layers
    device = build_device_context(device_payload)
    trajectory = build_trajectory(location_history)
    cognitive = derive_cognitive_state(calendar, temporal, behavioral)
    biological = derive_biological_signals(temporal, behavioral)
    goals = load_goals(db_goals)

    # Assemble world state
    world_state = {
        "_meta": {
            "schema_version": "2.0",
            "built_at": datetime.now().isoformat(),
            "lat": lat,
            "lng": lng,
        },
        "temporal": temporal,
        "location": location,
        "trajectory": trajectory,
        "environment": environment,
        "device": device,
        "calendar": calendar,
        "traffic": traffic,
        "nearby": nearby,
        "cognitive": cognitive,
        "biological": biological,
        "goals": goals,
    }

    # Final synthesis layer (LLM)
    if llm_client:
        world_state["inferred"] = await infer_intent(world_state, llm_client)
    else:
        world_state["inferred"] = {
            "probable_activity": "unknown",
            "likely_needs": [],
            "nudge_type": "none",
            "context_summary": "World state assembled. Inference layer requires LLM client.",
        }

    return world_state


# ─── SYSTEM PROMPT INJECTOR ───────────────────────────────────────────────────

def build_system_prompt(world_state: dict, user_preferences: dict) -> str:
    """
    Converts world state into the system prompt injected into every LLM call.
    This is what makes every response contextually aware.
    """
    ws = world_state
    t = ws.get("temporal", {})
    l = ws.get("location", {})
    e = ws.get("environment", {})
    c = ws.get("cognitive", {})
    b = ws.get("biological", {})
    g = ws.get("goals", {})
    inf = ws.get("inferred", {})

    context_summary = inf.get("context_summary", "")

    stale_goals = [goal["name"] for goal in g.get("stale_goals", [])]
    stale_str = f"Stale goals (not touched in 3+ days): {', '.join(stale_goals)}." if stale_goals else ""

    return f"""You are JARVIS — a proactive personal AI assistant.

## Current World State
Time: {t.get('time_of_day', 'unknown')} · {t.get('timestamp', '')[:16]}
Location: {l.get('district', '')}, {l.get('city', '')} ({l.get('location_type', 'unknown')} location)
Weather: {e.get('weather', {}).get('description', 'unknown')}, {e.get('weather', {}).get('temp_c', '?')}°C
User state: focus={c.get('estimated_focus', '?')}, fatigue={c.get('estimated_fatigue', '?')}, hunger_prob={b.get('hunger_probability', '?')}
Calendar: {ws.get('calendar', {}).get('events_today_total', 0)} meetings today, next: {ws.get('calendar', {}).get('next_event_tomorrow', {}) or 'none tomorrow'}
{stale_str}

## Inferred Context
{context_summary}

## Rules
- Every response must be grounded in the world state above
- Be specific: use actual city names, times, weather conditions
- Preferred response modality: {c.get('preferred_modality', 'text')}
- Preferred response length: {c.get('preferred_response_length', 'medium')}
- If hunger_probability > 0.7 and user mentions food: suggest nearby options with delivery links
- If rain forecast within 2h and user mentions going out: warn proactively
- Never say "I don't have access to" — use the world state you have
- Challenge the user when a better path exists

## User Profile
Name: {user_preferences.get('name', 'Clifford')}
Goals: {', '.join([g['name'] for g in g.get('active_goals', [])])}
"""


# ─── ENTRY POINT FOR TESTING ─────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    # Test with Lagos coordinates
    result = asyncio.run(build_world_state(
        lat=6.5244,
        lng=3.3792,
        device_payload={
            "battery_pct": 42,
            "charging": False,
            "headphones_connected": True,
            "network_type": "wifi",
            "network_quality": "strong",
            "platform": "ios",
        },
        location_history=[],
        behavioral={
            "hours_since_last_meal": 5.2,
            "typical_sleep_hour": 1.0,
            "typical_sleep_time": "01:00",
            "avg_sleep_hours": 6.0,
            "timezone": "Africa/Lagos",
        },
        db_goals=[
            {"name": "ACS application", "status": "active", "urgency": "high", "days_since_touched": 4},
            {"name": "UpJobs launch", "status": "active", "urgency": "high", "days_since_touched": 0},
            {"name": "Australia visa", "status": "active", "urgency": "medium", "days_since_touched": 2},
        ],
    ))

    print(json.dumps(result, indent=2, default=str))

    # Also print the system prompt
    system_prompt = build_system_prompt(result, {"name": "Clifford"})
    print("\n" + "="*60)
    print("SYSTEM PROMPT (injected into every LLM call):")
    print("="*60)
    print(system_prompt)