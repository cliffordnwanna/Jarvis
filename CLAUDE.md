# JARVIS v3 — Claude Code Context

## What this project is

JARVIS is a proactive personal AI for Clifford. Not a chatbot — a cognitive runtime that knows the user's world, relationships, and goals, and surfaces what matters before they ask.

**Live:** https://89.167.93.25.sslip.io
**Repo:** https://github.com/cliffordnwanna/Jarvis

---

## Stack

- **Backend:** FastAPI + LangGraph ReAct agent (`gpt-4o`), Python 3.12, uvicorn
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, PWA
- **DB:** Supabase PostgreSQL + pgvector (SERVICE_ROLE_KEY on backend — bypasses RLS)
- **Auth:** Supabase JWT — validated in `backend/auth.py`, user_id never trusted from client
- **Deploy:** PM2 + Caddy on VPS at 89.167.93.25, no Docker
- **Scheduler:** APScheduler (AsyncIOScheduler) — reminders every 5min, birthdays 8am UTC, strength signals midnight

---

## Project structure

```
backend/
  main.py              # FastAPI app, CORS, agent endpoint, scheduler startup
  agent.py             # LangGraph ReAct agent, BASE_SYSTEM_PROMPT, build_graph()
  auth.py              # JWT validation, get_current_user() Depends
  scheduler.py         # APScheduler jobs
  world_state.py       # World state builder (temporal, weather, location layers)
  nudge_engine.py      # Nudge evaluation logic
  db/
    postgres.py        # Supabase client (SERVICE_ROLE_KEY)
    cache.py           # World state cache (world_state table, TTL 300s)
    migrations/        # SQL migrations 001-004
  routers/
    context.py         # POST /context/update, GET /context/latest
    agent.py           # (streaming handled in main.py /agent endpoint)
    people.py          # CRUD for people
    goals.py           # Goal management
    nudges.py          # Nudge history
    reminders.py       # Reminder CRUD
    briefing.py        # Morning briefing
    voice.py           # OpenAI Realtime token
    memory.py          # RAG memory
    llm.py             # Direct LLM calls
  tools/
    world_tools.py     # get_world_state, send_nudge, get_nearby_places, get_travel_eta
    relationship_tools.py  # add_person, add_note_for_person, hybrid_search_notes_tool, create_reminder
    goal_tools.py      # get_goals, manage_goal
    search_tools.py    # web_search
  middleware/
    rate_limit.py      # 60 req/min default, 120/min for /voice

frontend/
  app/
    page.tsx           # Main chat page — SSE streaming, TimerWidget, VoiceMode
    login/page.tsx     # Supabase Auth UI, Google OAuth
    layout.tsx         # Root layout
    people/            # People directory
    goals/             # Goals page
    calendar/          # Calendar stub
    settings/          # Settings stub
  components/
    VoiceMode.tsx      # WebRTC Realtime + Web Speech API fallback
    TimerWidget.tsx    # Client-side countdown timers
    NudgePanel.tsx     # Nudge panel
    (cards...)         # WeatherCard, GoalReminderCard, etc.
  lib/
    supabase.ts        # Supabase client (ANON_KEY — frontend only)
    api.ts             # API helpers
    sensors.ts         # Browser sensor collection (GPS, timezone)

deploy/
  Caddyfile            # Caddy config — sslip.io TLS, /api/* strips prefix
  start.sh             # PM2 start (frontend on port 3001, backend on 8000)
  install.sh           # pip install + npm build
  update.sh            # git pull + pm2 restart
  setup-vps.sh         # One-time VPS hardening (firewall, fail2ban, SSH)
```

---

## Critical rules

### Security
- `SUPABASE_SERVICE_ROLE_KEY` is backend-only — never in frontend code or env
- `SUPABASE_ANON_KEY` is frontend-only
- `user_id` always comes from validated JWT (`get_current_user()`), never from request body
- No Redis anywhere — world state cached in Supabase `world_state` table

### CORS
Must be registered FIRST in main.py — Starlette reverses middleware order:
```python
app.add_middleware(CORSMiddleware, ...)   # first = outermost
app.middleware("http")(rate_limit)        # second = inner
```
Allowed origins: localhost:3000, 89.167.93.25.sslip.io, jarvis-eta-self.vercel.app

### World state structure
Built by `backend/world_state.py` → stored as:
```python
{
  "temporal": { "day_of_week", "hour", "minute", "date", "time_of_day", ... },
  "location": { "city", "area", "country", "lat", "lng" },
  "environment": { "weather": { "temp_c", "condition", "rain_probability_2h" } },
  ...
}
```
In `main.py`, read as: `world_state.get("temporal", {})` and `world_state.get("environment", {}).get("weather", {})`

### Agent system prompt injection
Every request injects: user_id, today's date, tomorrow's date, world state snapshot.
Agent never needs to call `get_world_state` unless it needs fresh data.

### Database constraints
- `relationship_notes.source` must be one of: `voice`, `text`, `chat_extraction`, `import`
- `relationship_events.event_type` must be one of: `birthday`, `follow_up`, `call`, `meeting`, `occasion`, `check_in`, `reminder`
- `relationship_events.person_id` — run `ALTER TABLE public.relationship_events ALTER COLUMN person_id DROP NOT NULL` in Supabase

### Timers vs reminders
- **Timers** (seconds to hours): client-side only, agent calls `create_timer` tool → returns `__TIMER__:seconds:label` sentinel → frontend parses and runs countdown
- **Reminders** (hours to days): stored in DB via `create_reminder` tool, scheduler fires nudge

### LangGraph version note
Use `prompt=` not `state_modifier=` in `create_react_agent()` — older versions use `state_modifier`.

---

## VPS details

- **IP:** 89.167.93.25
- **User:** deploy
- **App dir:** /home/deploy/apps/jarvis
- **Backend port:** 8000 (internal only)
- **Frontend port:** 3001 (internal only, 3000 is taken by upjobs)
- **Caddy:** proxies 443 → 3001 (frontend) and /api/* → 8000 (backend)
- **Python venv:** /home/deploy/apps/jarvis/venv

## Common commands

See `COMMANDS.md` for full reference. Most common:

```bash
# Deploy
cd /home/deploy/apps/jarvis && git pull && pm2 restart jarvis-backend

# Logs
pm2 logs jarvis-backend --lines 50 --nostream

# Full restart
cd /home/deploy/apps/jarvis && source venv/bin/activate
pm2 delete jarvis-backend && pm2 start "uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2" --name jarvis-backend --cwd /home/deploy/apps/jarvis
```
