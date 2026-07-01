import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import context, nudges, people, goals, memory, llm, briefing, voice, reminders, users
from backend.scheduler import start_scheduler
from backend.auth import get_current_user
from backend.db.cache import cache_get
from backend.middleware.rate_limit import rate_limit_middleware

app = FastAPI(title="JARVIS v3", version="3.0.0")

# CORS first — Starlette executes middleware in reverse registration order,
# so registering CORS first means it runs outermost (handles OPTIONS preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://89.167.93.25.sslip.io",
        "https://jarvis-eta-self.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limit registered after — runs inside CORS
app.middleware("http")(rate_limit_middleware)

app.include_router(context.router, prefix="/context", tags=["context"])
app.include_router(nudges.router, prefix="/nudges", tags=["nudges"])
app.include_router(people.router, prefix="/people", tags=["people"])
app.include_router(goals.router, prefix="/goals", tags=["goals"])
app.include_router(memory.router, prefix="/memory", tags=["memory"])
app.include_router(llm.router, prefix="/llm", tags=["llm"])
app.include_router(briefing.router, prefix="/briefing", tags=["briefing"])
app.include_router(voice.router, prefix="/voice", tags=["voice"])
app.include_router(reminders.router, prefix="/reminders", tags=["reminders"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.on_event("startup")
async def startup_event():
    start_scheduler()
    print("✓ Background scheduler started")

from fastapi import Request
from fastapi.responses import StreamingResponse
from backend.agent import build_graph, BASE_SYSTEM_PROMPT
from openai import AsyncOpenAI
import json

_openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_RECENT = 10
SUMMARY_THRESHOLD = 20


async def prepare_messages(messages: list, user_id: str = None) -> list:
    if len(messages) <= MAX_RECENT:
        return messages

    old = messages[:-MAX_RECENT]
    recent = messages[-MAX_RECENT:]

    if len(messages) <= SUMMARY_THRESHOLD:
        return messages  # between 10-20, send all

    old_text = "\n".join(
        f"{m['role'].upper()}: {m['content'][:300]}" for m in old
    )
    try:
        res = await _openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": (
                    "Summarise this conversation. Extract:\n"
                    "1. Key facts the user shared about themselves\n"
                    "2. Decisions or plans made\n"
                    "3. People mentioned and what was said about them\n"
                    "4. Goals or tasks discussed\n\n"
                    "Be specific and factual. Max 5 bullet points.\n\n"
                    + old_text
                )
            }],
            max_tokens=400,
        )
        summary = res.choices[0].message.content
        print(f"[context] summarised {len(old)} older messages into {len(summary)} chars")

        # Persist summary to Supabase so it survives session refreshes
        if user_id:
            try:
                from backend.db.postgres import get_supabase
                from datetime import datetime, timezone
                db = get_supabase()
                db.table("conversations").upsert({
                    "user_id": user_id,
                    "summary": summary,
                    "message_count": len(messages),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, on_conflict="user_id").execute()
            except Exception as e:
                print(f"[context] summary save failed: {e}")

        return [{"role": "user", "content": f"[Earlier conversation summary:\n{summary}]"}] + recent
    except Exception as e:
        print(f"[context] summarisation failed: {e}")
        return recent


def get_graph(system_prompt: str = None):
    return build_graph(system_prompt or BASE_SYSTEM_PROMPT)


# Module-level cache — one DB hit per user per backend restart
_user_profile_cache: dict = {}


def bust_profile_cache(user_id: str) -> None:
    _user_profile_cache.pop(user_id, None)

async def get_user_profile(user_id: str) -> dict:
    if user_id in _user_profile_cache:
        return _user_profile_cache[user_id]
    from backend.db.postgres import get_supabase
    db = get_supabase()
    try:
        res = db.table("users")\
            .select("display_name, timezone, morning_nudge_time, home_lat, home_lng, home_address, work_lat, work_lng, work_address")\
            .eq("id", user_id)\
            .maybe_single()\
            .execute()
        profile = res.data or {}
        _user_profile_cache[user_id] = profile
        print(f"[profile] Loaded for {user_id}: name={profile.get('display_name')}")
        return profile
    except Exception as e:
        print(f"[profile] Fetch error: {e}")
        return {}


@app.post("/agent")
async def agent_endpoint(request: Request, user_id: str = Depends(get_current_user)):
    body = await request.json()
    raw_messages = body.get("messages", [])
    messages = await prepare_messages(raw_messages, user_id=user_id)

    print(f"[agent] called by user={user_id}, last_message={messages[-1] if messages else 'none'}")

    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo

    now_utc = datetime.now(timezone.utc)
    tomorrow_str = (now_utc + timedelta(days=1)).strftime("%Y-%m-%d")

    world_state = await cache_get(user_id)

    # If cache is empty, the frontend may still be posting /context/update —
    # wait briefly and retry once before building the system prompt
    if not world_state:
        import asyncio as _asyncio
        await _asyncio.sleep(2)
        world_state = await cache_get(user_id)

    # Use user's local timezone from cached world state if available
    user_tz_str = "UTC"
    if world_state:
        user_tz_str = world_state.get("temporal", {}).get("timezone", "UTC") or "UTC"
    try:
        user_tz = ZoneInfo(user_tz_str)
        now_local = datetime.now(user_tz)
    except Exception:
        now_local = now_utc

    today_str = now_local.strftime("%A, %B %d, %Y")
    time_str = now_local.strftime("%H:%M")
    tomorrow_str = (now_local + timedelta(days=1)).strftime("%Y-%m-%d")

    day_after_str = (now_local + timedelta(days=2)).strftime("%Y-%m-%d")

    if world_state:
        temporal = world_state.get("temporal", {})
        location = world_state.get("location", {})
        weather  = world_state.get("environment", {}).get("weather", {})

        time_of_day = temporal.get("time_of_day", "")
        district    = location.get("district", "")
        city        = location.get("city", "")
        state       = location.get("state", "")
        country     = location.get("country", "")
        _loc_parts = []
        if district and district.lower() != city.lower():
            _loc_parts.append(district)
        if city:
            _loc_parts.append(city)
        if state and state.lower() != city.lower():
            _loc_parts.append(state)
        if country:
            _loc_parts.append(country)
        location_str = ", ".join(_loc_parts)

        temp_c         = weather.get("temp_c")
        feels_like     = weather.get("feels_like_c")
        condition      = weather.get("condition", "")
        description    = weather.get("description", "") or condition
        rain_1h        = weather.get("forecast_1h_rain_prob", 0) or 0
        precip_mm      = weather.get("precipitation_mm", 0) or 0
        is_raining     = precip_mm > 0.1
        tomorrow_rain  = weather.get("tomorrow_rain_prob", 0) or 0
        tomorrow_cond  = weather.get("tomorrow_condition", "")
        uv             = weather.get("uv_index", 0)
        humidity       = weather.get("humidity_pct", 0)
        wind           = weather.get("wind_speed_kmh", 0)

        if is_raining:
            rain_status = f"Raining now ({precip_mm}mm). {int(rain_1h * 100)}% chance next hour."
        elif rain_1h > 0.5:
            rain_status = f"No rain now but {int(rain_1h * 100)}% chance in the next hour."
        else:
            rain_status = f"No rain. {int(rain_1h * 100)}% chance next hour."

        lat = location.get("lat") or world_state.get("_meta", {}).get("lat")
        lng = location.get("lng") or world_state.get("_meta", {}).get("lng")
        coords_line = f"GPS coordinates: {lat}, {lng}\n" if lat and lng else ""

        world_context = (
            f"DATE: {today_str} | TIME: {time_str} ({user_tz_str}) | {time_of_day}\n"
            f"Today ISO: {now_local.strftime('%Y-%m-%d')} | Tomorrow: {tomorrow_str} | Day after: {day_after_str}\n"
            f"For dates beyond tomorrow, calculate from today's ISO date and day-of-week.\n"
            f"LOCATION: {location_str}{(' | GPS: ' + str(lat) + ', ' + str(lng)) if lat and lng else ''}\n"
            f"WEATHER: {temp_c}°C (feels {feels_like}°C), {description}. {rain_status} Tomorrow: {tomorrow_cond} {int(tomorrow_rain * 100)}% rain.\n"
        )
    else:
        world_context = (
            f"DATE: {today_str} | TIME: {time_str}\n"
            f"Today ISO: {now_local.strftime('%Y-%m-%d')} | Tomorrow: {tomorrow_str} | Day after: {day_after_str}\n"
            "Location/weather not available — user needs to grant location permission.\n"
        )

    profile = await get_user_profile(user_id)
    user_name = profile.get("display_name") or ""

    # On a fresh session (≤2 messages), load the last saved conversation summary
    conversation_context = ""
    if len(messages) <= 2:
        try:
            from backend.db.postgres import get_supabase
            db = get_supabase()
            result = db.table("conversations")\
                .select("summary, updated_at")\
                .eq("user_id", user_id)\
                .order("updated_at", desc=True)\
                .limit(1)\
                .maybe_single()\
                .execute()
            if result and result.data and result.data.get("summary"):
                conversation_context = (
                    "PREVIOUS CONVERSATION CONTEXT:\n"
                    + result.data["summary"]
                    + "\n\n(New session — use this context to continue naturally.)\n\n"
                )
                print(f"[agent] Loaded previous conversation summary for {user_id}")
        except Exception as e:
            print(f"[agent] Failed to load conversation summary: {e}")

    name_line = f"USER'S NAME: {user_name} — address them by this name.\n" if user_name else ""
    home_lat  = profile.get("home_lat")
    home_lng  = profile.get("home_lng")
    home_addr = profile.get("home_address") or "Home"
    work_lat  = profile.get("work_lat")
    work_lng  = profile.get("work_lng")
    work_addr = profile.get("work_address") or "Work"
    home_line = (
        f"Home: {home_addr} (coordinates: {home_lat}, {home_lng})\n"
        f"→ For directions home: get_route_and_traffic(user_id, dest_lat={home_lat}, dest_lng={home_lng}, destination_label='Home')\n"
        if home_lat and home_lng else ""
    )
    work_line = (
        f"Work: {work_addr} (coordinates: {work_lat}, {work_lng})\n"
        f"→ For directions to work: get_route_and_traffic(user_id, dest_lat={work_lat}, dest_lng={work_lng}, destination_label='Work')\n"
        if work_lat and work_lng else ""
    )
    system_prompt = (
        f"USER ID (use this exact UUID for ALL tool calls that need user_id): {user_id}\n"
        + name_line
        + home_line
        + work_line
        + conversation_context
        + world_context
        + "\n"
        + BASE_SYSTEM_PROMPT
    )

    async def stream():
        graph = get_graph(system_prompt)
        async for chunk in graph.astream(
            {"messages": messages},
            config={"configurable": {"user_id": user_id}},
        ):
            print(f"[agent] chunk keys: {list(chunk.keys())}")
            for node_key in chunk:
                if node_key == "tools":
                    continue  # never yield raw tool results
                node_output = chunk[node_key]
                if not isinstance(node_output, dict):
                    continue
                for msg in node_output.get("messages", []):
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    if not isinstance(content, str) or not content.strip():
                        continue
                    # Skip raw JSON tool results that leaked through
                    stripped = content.strip()
                    if stripped.startswith('{"error"') or stripped.startswith('[{'):
                        continue
                    print(f"[agent] yielding: {content[:80]}")
                    yield f"data: {json.dumps({'content': content})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/test/morning-briefing")
async def test_morning_briefing():
    from backend.scheduler import morning_weather_briefing
    await morning_weather_briefing()
    return {"status": "done"}


@app.get("/world-state")
async def get_world_state(user_id: str = Depends(get_current_user)):
    state = await cache_get(user_id)
    if not state:
        return {"status": "empty", "message": "No world state yet. POST to /context/update first."}
    return state
