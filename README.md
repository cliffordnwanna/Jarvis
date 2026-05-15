# JARVIS v2 — Cognitive Runtime

A proactive personal AI that understands your world state and nudges you proactively.

```
PWA (Next.js)
  │ CopilotChat ──── reactive Q&A + generative UI cards (L3 pattern)
  │ NudgePanel  ──── proactive cards from agent.state.nudges (L6 pattern)
  │ useAgent    ──── shared state sync via AG-UI protocol
  │
  ↕ AG-UI protocol (WebSocket)
  │
FastAPI backend
  │ LangGraph agent ── CopilotKit middleware
  │ Tools: send_nudge, manage_goals, web_search, update_world_state
  │
  ├── World State Engine (world_state.py)
  │     Open-Meteo · Nominatim · Overpass · TomTom · Google Calendar
  │
  ├── PostgreSQL ── behavioral graph, goals, nudge history
  └── Redis      ── world state cache (TTL 300s)
```

## Architecture

**Proactive personal AI. NOT a chatbot wrapper.**

- **Backend**: FastAPI + LangGraph agent exposed via AG-UI protocol
- **Frontend**: Next.js PWA with CopilotKit (chat + generative UI cards + shared state)
- **DB**: PostgreSQL (behavioral memory) + Redis (world state cache)
- **LLM**: Groq primary (free), OpenAI fallback

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/jarvis-v2.git
cd jarvis-v2
```

### 2. Configure Environment

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
```

**Edit `.env`** with your API keys:
```
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
TOMTOM_API_KEY=...
GOOGLE_CALENDAR_CLIENT_ID=...
GOOGLE_CALENDAR_CLIENT_SECRET=...
```

All other services are free (no key required):
- Weather (Open-Meteo)
- Geocoding (Nominatim)
- Nearby POIs (Overpass)
- Web search (DuckDuckGo)

### 3. Start Services

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Postgres: localhost:5432
- Redis: localhost:6379

### 4. First Steps

1. Open http://localhost:3000
2. Grant location permission to the PWA
3. Type: **"What should I eat right now?"** — JARVIS renders a food card
4. Type: **"I want to learn Spanish"** — JARVIS creates a goal
5. Watch for **nudges** in the right panel (proactive suggestions)

## File Structure

```
jarvis-v2/
├── backend/
│   ├── main.py                 # FastAPI app + LangGraph endpoint
│   ├── agent.py                # LangGraph agent state machine
│   ├── world_state.py          # Sensor fusion engine (WIP)
│   ├── nudge_engine.py         # Proactive nudge logic (WIP)
│   ├── tools/
│   │   ├── world_tools.py      # update_world_state, send_nudge
│   │   ├── goal_tools.py       # manage_goals, get_goals
│   │   └── search_tools.py     # web_search (DuckDuckGo)
│   ├── routers/
│   │   ├── context.py          # POST /context — sensor data
│   │   └── memory.py           # GET/POST /memory — goals
│   ├── db/
│   │   ├── postgres.py         # Schema + async queries
│   │   ├── redis_client.py     # World state cache
│   │   └── migrations/
│   │       └── 001_init.sql    # Tables: users, goals, nudges, etc.
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx          # Root CopilotKit wrapper
│   │   ├── page.tsx            # Main UI (chat + nudge panel)
│   │   └── globals.css         # Dark theme
│   ├── components/
│   │   ├── WeatherCard.tsx     # Generative UI card for weather
│   │   ├── TrafficCard.tsx     # Traffic / ETA card
│   │   ├── FoodOptionsCard.tsx # Restaurant suggestions
│   │   ├── GoalReminderCard.tsx# Goal nudges
│   │   ├── NudgePanel.tsx      # Right sidebar with nudges + goals
│   │   ├── VoiceButton.tsx     # Voice input (Web Speech API)
│   │   └── WorldStateDebug.tsx # JSON viewer for debugging
│   ├── lib/
│   │   ├── sensors.ts          # GPS, battery, network, headphones
│   │   └── api.ts              # HTTP client
│   ├── public/
│   │   ├── manifest.json       # PWA metadata
│   │   └── sw.js               # Service worker
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── .env.local.example
│
├── docker-compose.yml
├── Dockerfile                  # Backend
├── frontend/Dockerfile         # Frontend
└── README.md
```

## Frontend Patterns (from CopilotKit Course)

### L3: Generative UI Cards

Agent calls tools → React renders structured cards instead of text.

```tsx
useComponent({
  name: "weatherCard",
  parameters: z.object({...}),
  render: WeatherCard,
})
```

When agent calls `weatherCard({ temp_c: 22, ... })`, the frontend renders it as a visual card.

### L6: Shared State + Frontend Tools

Agent and frontend sync state bidirectionally via `useAgent()`:

```tsx
const { agent } = useAgent()
const nudges = agent.state?.nudges ?? []

useFrontendTool({
  name: "openNudgePanel",
  handler: async () => {
    agent.setState({ panel_open: true })
  },
})
```

### Reactive Sensors

Every 10 seconds, the PWA sends GPS + device state to backend:

```tsx
useEffect(() => {
  setInterval(() => pushSensors(backendUrl), 10000)
}, [])
```

Backend caches in Redis, agent enriches with weather/traffic.

## Backend Patterns

### LangGraph State Machine

```python
class AgentState(TypedDict):
    world_state: dict      # Full sensor snapshot
    nudges: list[Nudge]    # Pending proactive suggestions
    goals: list[Goal]      # User goals (editable from frontend)
    panel_open: bool       # UI state sync
```

### Tools as State Updates

Tools don't just return values — they return `Command(update={...})` to mutate shared state:

```python
@tool
def send_nudge(nudge_type: str, ..., runtime: ToolRuntime) -> Command:
    nudge = {...}
    return Command(update={
        "nudges": runtime.state.get("nudges", []) + [nudge],
        "panel_open": priority == "high",
    })
```

### Reactive Modes

**REACTIVE**: User asks → agent uses world_state context → renders card

**PROACTIVE**: World state changes → agent checks conditions → sends nudge

```python
system_prompt = """
PROACTIVE mode:
- Rain in 1h → send_nudge type=weather, priority=high
- Hunger > 0.75 → send_nudge type=food, priority=medium
- Goal stale > 3 days → send_nudge type=goal, priority=low
"""
```

## Free API Keys

1. **Groq** (LLM): https://console.groq.com — sign up, copy API key
2. **TomTom** (Traffic): https://developer.tomtom.com — register, 2500 req/day free tier
3. Everything else: **no key required**
   - Weather: Open-Meteo
   - Geocoding: Nominatim
   - POI search: Overpass
   - Web search: DuckDuckGo

## WIP (Next Steps)

- [ ] `world_state.py` — Sensor fusion engine that calls Open-Meteo, TomTom, Nominatim, Overpass
- [ ] `nudge_engine.py` — Rule engine for proactive triggers
- [ ] Google Calendar integration
- [ ] Meal logging + hunger prediction
- [ ] Mobile app deep-link for ordering

---

**Status**: Pre-alpha. Core architecture works. World state enrichment and nudge logic are stub implementations.
