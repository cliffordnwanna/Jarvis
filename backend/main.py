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

async def get_user_profile(user_id: str) -> dict:
    if user_id in _user_profile_cache:
        return _user_profile_cache[user_id]
    from backend.db.postgres import get_supabase
    db = get_supabase()
    try:
        res = db.table("users")\
            .select("display_name, timezone, morning_nudge_time")\
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

    # Pre-compute next occurrence of each weekday (always future)
    def next_weekday_date(target_weekday: int) -> str:
        days_ahead = (target_weekday - now_local.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (now_local + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    next_days = {
        "Monday":    next_weekday_date(0),
        "Tuesday":   next_weekday_date(1),
        "Wednesday": next_weekday_date(2),
        "Thursday":  next_weekday_date(3),
        "Friday":    next_weekday_date(4),
        "Saturday":  next_weekday_date(5),
        "Sunday":    next_weekday_date(6),
    }

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

        world_context = f"""=== CURRENT DATE & TIME (USE THESE EXACT VALUES) ===
Today is: {today_str}
Current time: {time_str} ({user_tz_str})
Time of day: {time_of_day}
Today ISO: {now_local.strftime("%Y-%m-%d")}
Tomorrow ISO: {tomorrow_str}

Next weekdays:
- Next Monday: {next_days['Monday']}
- Next Tuesday: {next_days['Tuesday']}
- Next Wednesday: {next_days['Wednesday']}
- Next Thursday: {next_days['Thursday']}
- Next Friday: {next_days['Friday']}
- Next Saturday: {next_days['Saturday']}
- Next Sunday: {next_days['Sunday']}

IMPORTANT: Always use ISO dates above for reminders. Never calculate dates yourself.

=== CURRENT LOCATION ===
Neighbourhood: {district}
City: {city}
State: {state}
Country: {country}
Full location: {location_str}

=== CURRENT WEATHER ===
Temperature: {temp_c}°C (feels like {feels_like}°C)
Condition: {description}
Rain: {rain_status}
Tomorrow: {tomorrow_cond}, rain probability {int(tomorrow_rain * 100)}%
Humidity: {humidity}%
Wind: {wind} km/h
UV index: {uv}
"""
    else:
        world_context = f"""=== CURRENT DATE & TIME ===
Today is: {today_str}
Current time: {time_str}
Today ISO: {now_local.strftime("%Y-%m-%d")}
Tomorrow ISO: {tomorrow_str}

Next weekdays:
- Next Monday: {next_days['Monday']}
- Next Tuesday: {next_days['Tuesday']}
- Next Wednesday: {next_days['Wednesday']}
- Next Thursday: {next_days['Thursday']}
- Next Friday: {next_days['Friday']}

World state not available yet — user needs to grant location permission.
"""

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
    system_prompt = (
        f"USER ID (use this exact UUID for ALL tool calls that need user_id): {user_id}\n"
        + name_line
        + f"TODAY'S DATE: {today_str}\n"
        + f"TOMORROW'S DATE: {tomorrow_str} (use this exact date when user says 'tomorrow')\n\n"
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
