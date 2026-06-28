import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import context, nudges, people, goals, memory, llm, briefing, voice, reminders
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


@app.on_event("startup")
async def startup_event():
    start_scheduler()
    print("✓ Background scheduler started")

from fastapi import Request
from fastapi.responses import StreamingResponse
from backend.agent import build_graph, BASE_SYSTEM_PROMPT
import json

def get_graph(system_prompt: str = None):
    return build_graph(system_prompt or BASE_SYSTEM_PROMPT)


@app.post("/agent")
async def agent_endpoint(request: Request, user_id: str = Depends(get_current_user)):
    body = await request.json()
    messages = body.get("messages", [])

    print(f"[agent] called by user={user_id}, last_message={messages[-1] if messages else 'none'}")

    # Inject world state + user_id + real date into system prompt
    from datetime import datetime, timezone, timedelta
    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%A, %B %d, %Y")  # e.g. "Saturday, June 28, 2026"
    tomorrow_str = (now_utc + timedelta(days=1)).strftime("%Y-%m-%d")

    world_state = await cache_get(user_id)
    if world_state:
        loc = world_state.get("location", {})
        wx = world_state.get("weather", {})
        t = world_state.get("time", {})
        world_context = (
            f"CURRENT WORLD STATE (already fetched — do not call get_world_state):\n"
            f"- Time: {t.get('day_of_week')} {t.get('hour', 0):02d}:{str(t.get('minute', 0)).zfill(2)}, {t.get('date')}\n"
            f"- Location: {loc.get('city')}, {loc.get('country')}\n"
            f"- Weather: {wx.get('temp_c')}°C, {wx.get('condition')}, rain {wx.get('rain_probability_2h', 0)}%\n"
        )
    else:
        world_context = "WORLD STATE: not available yet (user may not have granted location).\n"

    system_prompt = (
        f"USER ID (use this exact UUID for ALL tool calls that need user_id): {user_id}\n"
        f"TODAY'S DATE: {today_str}\n"
        f"TOMORROW'S DATE: {tomorrow_str} (use this exact date when user says 'tomorrow')\n\n"
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


@app.get("/world-state")
async def get_world_state(user_id: str = Depends(get_current_user)):
    state = await cache_get(user_id)
    if not state:
        return {"status": "empty", "message": "No world state yet. POST to /context/update first."}
    return state
