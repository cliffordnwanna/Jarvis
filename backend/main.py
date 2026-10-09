import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import context, nudges, people, goals, memory, llm, briefing, voice, reminders, users, conversations
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
        "http://localhost:3001",
        "http://127.0.0.1:3001",
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
app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])


from fastapi import Request
from fastapi.responses import StreamingResponse
from backend.agent import build_graph
from backend.db.checkpointer import get_checkpointer, close_checkpointer
from backend.context.builder import build_context, _count_tokens
from backend.utils.titles import generate_title
from backend.memory.mem0_client import remember as mem0_remember, get_all_authoritative as mem0_get_all, delete_all as mem0_delete_all
from openai import AsyncOpenAI
import asyncio
import json


@app.on_event("startup")
async def startup_event():
    # Fails loudly at boot instead of as a confusing failed chat request
    # later -- ChatOpenAI/AsyncOpenAI don't validate the key until the
    # first real API call, so a missing key previously surfaced only when
    # a user's first message silently errored.
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set -- the agent cannot start without it.")

    start_scheduler()
    print("✓ Background scheduler started")

    checkpointer = await get_checkpointer()
    app.state.graph = build_graph(checkpointer=checkpointer)
    print("✓ Agent graph built once at startup (PostgresSaver checkpointer)")


@app.on_event("shutdown")
async def shutdown_event():
    await close_checkpointer()
    print("✓ Checkpointer connection pool closed")

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


async def persist_message(conversation_id: str, user_id: str, role: str, content: str) -> None:
    """Fire-and-forget: write one turn to the messages table. Non-fatal on failure."""
    if not content or not content.strip():
        return
    try:
        from backend.db.postgres import get_supabase
        db = get_supabase()
        db.table("messages").insert({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
        }).execute()
    except Exception as e:
        print(f"[messages] persist error (non-fatal): {e}")


async def get_or_create_conversation(conversation_id: str, user_id: str) -> bool:
    """
    Ensures a conversations row exists for this id. The frontend generates
    the id client-side (crypto.randomUUID()) and this call makes it durable
    on first use — so the same id works as both the LangGraph thread_id and
    the conversations.id foreign key messages point at.

    Returns True if this call created the row (i.e. this is the first
    message in the conversation) — the signal used to trigger title
    generation, which is more reliable than counting messages afterward.
    """
    from backend.db.postgres import get_supabase
    db = get_supabase()
    try:
        existing = db.table("conversations").select("id").eq("id", conversation_id).maybe_single().execute()
        if existing and existing.data:
            return False
    except Exception as e:
        print(f"[conversations] lookup error: {e}")

    try:
        db.table("conversations").insert({
            "id": conversation_id,
            "user_id": user_id,
            "title": "New conversation",
        }).execute()
        return True
    except Exception as e:
        print(f"[conversations] create error (non-fatal): {e}")
        return False


async def _update_title_async(conversation_id: str, first_message: str) -> None:
    """Fire-and-forget: generate and save a real title. Non-fatal on failure."""
    try:
        from backend.db.postgres import get_supabase
        title = await generate_title(first_message)
        db = get_supabase()
        db.table("conversations").update({"title": title}).eq("id", conversation_id).execute()
        print(f"[title] set '{title}' for conversation {conversation_id}")
    except Exception as e:
        print(f"[title] update failed (non-fatal): {e}")


@app.post("/agent")
async def agent_endpoint(request: Request, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    body = await request.json()
    raw_messages = body.get("messages", [])
    thread_id = body.get("thread_id") or f"default-{user_id}"
    is_first_message = await get_or_create_conversation(thread_id, user_id)

    # The checkpointer owns conversation history for this thread — only the
    # newest user message needs to go to the graph; LangGraph replays the
    # rest from Postgres via thread_id. prepare_messages()'s summarization
    # logic operated on a full client-sent array, which no longer applies
    # here; it's left in place but unused by this endpoint.
    user_turn = raw_messages[-1] if raw_messages else None
    messages = [user_turn] if user_turn else []

    if is_first_message and user_turn and user_turn.get("content"):
        background_tasks.add_task(_update_title_async, thread_id, user_turn["content"])

    print(f"[agent] called by user={user_id}, thread={thread_id}, last_message={messages[-1] if messages else 'none'}")

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

    # On a fresh session (no checkpointed history yet for this thread), load
    # the last saved conversation summary as a bridge for continuity
    conversation_context = ""
    if len(messages) <= 1:
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

    # Pre-formatted profile text (name + home/work route-tool hints) — kept
    # as rich text from the existing logic rather than build_context()'s
    # simpler internal formatter, so proactive traffic/weather tool-call
    # guidance isn't silently lost.
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
    profile_text = (f"USER ID (use this exact UUID for ALL tool calls that need user_id): {user_id}\n"
                     + name_line + home_line + work_line) or None
    world_state_text = (conversation_context + world_context) or None

    user_turn_content = user_turn.get("content", "") if user_turn else ""

    from backend.db.postgres import get_supabase
    context_result = await build_context(
        user_id=user_id,
        conversation_id=thread_id,
        current_message=user_turn_content,
        world_state=world_state,
        supabase=get_supabase(),
        profile_text=profile_text,
        world_state_text=world_state_text,
    )
    system_prompt = context_result.text

    async def stream():
        graph = app.state.graph
        assistant_content = ""
        async for chunk in graph.astream(
            {"messages": messages, "system_prompt": system_prompt, "user_id": user_id},
            config={"configurable": {"thread_id": thread_id, "user_id": user_id}},
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
                    assistant_content += content
                    yield f"data: {json.dumps({'content': content})}\n\n"
        yield "data: [DONE]\n\n"

        print(f"[agent] post-stream: persisting + extracting memory for thread={thread_id}")
        await persist_message(thread_id, user_id, "user", user_turn_content)
        await persist_message(thread_id, user_id, "assistant", assistant_content)

        # Mem0 extraction — only after the assistant message is fully
        # assembled (post-stream), never mid-stream. Awaited directly here
        # rather than via asyncio.create_task(): by this point the client
        # has already received the full "data: [DONE]" stream, so this adds
        # no perceived latency, and — critically — a bare create_task()
        # scheduled this late has no guaranteed lifetime once the generator
        # (and the StreamingResponse closing it) finishes; it can be
        # silently cancelled before it ever runs. Confirmed this was
        # happening: a direct conflict-resolution test (telling JARVIS a
        # new fact that should supersede an old one) showed the new fact
        # never reached Mem0 at all, with no error logged — the task was
        # being dropped, not failing loudly. Awaiting it here is what
        # actually guarantees execution.
        if user_turn_content and assistant_content:
            await mem0_remember([
                {"role": "user", "content": user_turn_content},
                {"role": "assistant", "content": assistant_content},
            ], user_id=user_id)
            print(f"[agent] post-stream: mem0_remember() returned for thread={thread_id}")
        else:
            print(f"[agent] post-stream: skipped mem0_remember (empty user_turn_content or assistant_content)")

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


# TEMPORARY — debug/dev endpoints. Remove before Phase 3.
@app.get("/debug/context")
async def debug_context(user_id: str = Depends(get_current_user)):
    from backend.db.postgres import get_supabase
    result = await build_context(
        user_id=user_id,
        conversation_id="debug-test",
        current_message="test message",
        world_state=None,
        supabase=get_supabase(),
    )
    return {
        "token_count": result.total_tokens,
        "layers": [
            {"name": l.name, "included": l.included,
             "tokens": l.token_count, "reason": l.reason}
            for l in result.layers
        ],
        "text_preview": result.text[:500],
    }


@app.get("/debug/memories")
async def debug_memories(user_id: str = Depends(get_current_user)):
    """
    List all stored Mem0 memories via direct Postgres — development only.
    Uses direct SQL, not Mem0's own get_all(): confirmed by direct testing
    that get_all() underreports real row counts in this config.
    """
    memories = await mem0_get_all(user_id)
    return {
        "count": len(memories),
        "memories": memories,
    }


@app.delete("/debug/memories")
async def clear_all_memories(user_id: str = Depends(get_current_user)):
    """Wipe all Mem0 memories — use to start fresh."""
    deleted = await mem0_delete_all(user_id)
    return {"deleted": deleted}
