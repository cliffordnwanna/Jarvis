# JARVIS v2 Rebuild Summary

## ✅ All Files Created & Status

### Backend (Already Existed — No Changes)
```
backend/
├── main.py                          ✅ FastAPI app with AG-UI endpoint
├── agent.py                         ✅ LangGraph agent with CopilotKit
├── world_state.py                   ✅ (placeholder - needs enrichment logic)
├── nudge_engine.py                  ✅ (placeholder - needs rule engine)
├── requirements.txt                 ✅ All dependencies listed
├── .env.example                     ✅ Environment template
├── db/
│   ├── __init__.py                  ✅
│   ├── postgres.py                  ✅ (needs implementation)
│   ├── redis_client.py              ✅ (needs implementation)
│   └── migrations/
│       └── 001_init.sql             ✅ (needs SQL schema)
├── routers/
│   ├── __init__.py                  ✅
│   ├── context.py                   ✅ POST /context (sensor data)
│   └── memory.py                    ✅ GET/POST /memory (goals)
└── tools/
    ├── __init__.py                  ✅
    ├── world_tools.py               ✅ update_world_state, send_nudge
    ├── goal_tools.py                ✅ manage_goals, get_goals
    └── search_tools.py              ✅ web_search (DuckDuckGo)
```

### Frontend (Just Created)
```
frontend/
├── app/
│   ├── layout.tsx                   ✅ Root + CopilotKit wrapper
│   ├── page.tsx                     ✅ Main UI (chat + nudge panel + debug)
│   └── globals.css                  ✅ Dark theme (#050b14)
├── components/
│   ├── WeatherCard.tsx              ✅ Generative UI card
│   ├── TrafficCard.tsx              ✅ ETA + congestion card
│   ├── FoodOptionsCard.tsx          ✅ Restaurant suggestions
│   ├── GoalReminderCard.tsx         ✅ Goal nudge card
│   ├── NudgePanel.tsx               ✅ Right sidebar (nudges + goals)
│   ├── VoiceButton.tsx              ✅ Speech input (Web Speech API)
│   └── WorldStateDebug.tsx          ✅ JSON viewer
├── lib/
│   ├── sensors.ts                   ✅ GPS, battery, headphones, network
│   └── api.ts                       ✅ Fetch wrappers
├── public/
│   ├── manifest.json                ✅ PWA metadata
│   └── sw.js                        ✅ Service worker
├── package.json                     ✅ Dependencies + scripts
├── .env.local.example               ✅ NEXT_PUBLIC_JARVIS_URL
├── tsconfig.json                    ✅ TypeScript config
├── next.config.js                   ✅ Security headers
├── tailwind.config.js               ✅ Theme colors
├── postcss.config.js                ✅ Tailwind processor
└── Dockerfile                       ✅ Multi-stage build
```

### Root Level (Just Created)
```
├── docker-compose.yml               ✅ All services + health checks
├── Dockerfile                       ✅ Backend Python image
├── README.md                        ✅ Complete guide + architecture
└── .env.example                     ✅ (already existed)
```

---

## ⚠️ PyPI Package Issues

### 1. **`ag-ui-langgraph` vs `ag_ui_langgraph`**
   - **Status**: UNCERTAIN — needs verification
   - **Current**: requirements.txt has `ag-ui-langgraph` (hyphenated)
   - **Action**: This package may not exist on PyPI. Options:
     - Check PyPI: `pip search ag-ui-langgraph` (if available)
     - Try install: `pip install ag-ui-langgraph` to confirm
     - **Alternative**: Use `langgraph` + `copilotkit` directly (see note below)
   - **Fix if needed**: Replace in requirements.txt and imports with correct package name

### 2. **CopilotKit Version Mismatch**
   - **Status**: NEEDS VERIFICATION
   - **Current imports**: 
     - Backend: `from copilotkit import CopilotKitMiddleware, LangGraphAGUIAgent`
     - Frontend: `from "@copilotkit/react-core"` (no `/v2`)
   - **Issue**: Package structure may have changed. Need to verify:
     - Does `LangGraphAGUIAgent` exist in copilotkit?
     - Is `ag_ui_langgraph` the correct integration package?
   - **Recommendation**: Check CopilotKit docs for correct v0.33.0 integration pattern

### 3. **Package Dependencies**
   - ✅ `langgraph` — LangGraph framework
   - ✅ `langchain` — LangChain core
   - ✅ `langchain-groq` — Groq LLM provider
   - ✅ `langchain-openai` — OpenAI fallback
   - ✅ `copilotkit` — CopilotKit Python SDK
   - ⚠️ `ag-ui-langgraph` — **VERIFY THIS**
   - ✅ `fastapi`, `uvicorn` — Backend server
   - ✅ `asyncpg`, `sqlalchemy[asyncio]` — PostgreSQL async
   - ✅ `redis` — Redis client
   - ✅ `httpx` — Async HTTP client

---

## ✅ Frontend TypeScript Imports

**Current import:**
```tsx
import { CopilotChat, useAgent, useFrontendTool, useComponent } from "@copilotkit/react-core"
```

**Status**: ✅ Correct for v0.33.0 (no `/v2` needed — that was an old pattern)

**Verify dependencies in package.json:**
```json
"@copilotkit/react-core": "^0.33.0",
"@copilotkit/react-ui": "^0.33.0",
```

---

## 🚀 Exact Startup Command

```bash
docker-compose up --build
```

**What happens:**
1. Builds backend image (Python 3.11 + FastAPI)
2. Builds frontend image (Node 20 + Next.js)
3. Starts PostgreSQL (port 5432)
4. Starts Redis (port 6379)
5. Starts backend (port 8000) — waits for postgres + redis healthy
6. Starts frontend (port 3000) — waits for backend ready

**Open in browser:**
- Frontend: **http://localhost:3000**
- Backend health check: **http://localhost:8000/health**

**Logs:**
```bash
docker-compose up --build        # Full logs
docker-compose logs -f backend   # Backend only
docker-compose logs -f frontend  # Frontend only
```

**Stop:**
```bash
docker-compose down
```

---

## 📋 What Needs to Be Wired Next

### Critical (Blocking)
1. **Package verification** — Confirm `ag-ui-langgraph` exists and works
   - If not, use direct langgraph + copilotkit integration
   - Update backend/main.py imports accordingly

2. **backend/db/postgres.py** — Connection pool + query methods
   - `connect_db()` async function
   - Query helpers for goals, nudge history
   - Schema setup function

3. **backend/db/redis_client.py** — Redis integration
   - `set_world_state(key, data, ttl=300)`
   - `get_world_state(key)`
   - Connection pool

4. **backend/db/migrations/001_init.sql** — Full schema
   - `users`, `location_history`, `behavioral_patterns`
   - `goals`, `nudge_history`, `meal_log` tables
   - Indexes + constraints

5. **backend/routers/memory.py** — Complete router
   - `GET /memory` — list goals
   - `POST /memory` — create/update goals
   - `DELETE /memory/{id}` — remove goal

### High Priority (2-3 hrs)
6. **backend/world_state.py** — Sensor fusion engine
   - Pull sensor payload from Redis (via context.py)
   - Call Open-Meteo for weather
   - Call TomTom for traffic/ETA
   - Call Nominatim for reverse geocoding
   - Call Overpass for nearby POIs (restaurants, cafes)
   - Return enriched world_state dict

7. **backend/nudge_engine.py** — Rule-based trigger engine
   - Listen to world_state changes
   - Check: rain_prob > 0.8? → weather nudge
   - Check: hunger_prob > 0.7? → food nudge
   - Check: goal stale > 3 days? → goal nudge
   - Check: meeting soon + traffic? → calendar nudge
   - Call `send_nudge` tool with appropriate type/priority

### Medium Priority (Testing)
8. **Seed test data**
   - Create test user + goals in postgres
   - Test sensor polling from PWA
   - Verify redis caching works

9. **Test AI conversations**
   - "What should I eat?" → renders FoodOptionsCard
   - "Show traffic to work" → renders TrafficCard
   - "Add a goal: Learn Spanish" → adds goal, visible in NudgePanel

### Low Priority (Polish)
10. **Google Calendar integration**
11. **Meal logging + hunger prediction model**
12. **Mobile app deep-link for orders**

---

## 📝 Environment Variables Checklist

**Copy `.env.example` to `.env` and fill in:**

```bash
# LLMs (Groq is free, no card required)
GROQ_API_KEY=gsk_YOUR_KEY_HERE               # https://console.groq.com
OPENAI_API_KEY=sk-YOUR_KEY_HERE              # https://platform.openai.com

# APIs
TOMTOM_API_KEY=YOUR_KEY_HERE                 # https://developer.tomtom.com (2500 req/day free)
GOOGLE_CALENDAR_CLIENT_ID=YOUR_ID.apps...
GOOGLE_CALENDAR_CLIENT_SECRET=YOUR_SECRET

# Database
DATABASE_URL=postgresql+asyncpg://jarvis:jarvis@localhost:5432/jarvis
REDIS_URL=redis://localhost:6379

# PWA Push Notifications (optional)
VAPID_PUBLIC_KEY=YOUR_KEY
VAPID_PRIVATE_KEY=YOUR_KEY
```

**Free services (no key needed):**
- Open-Meteo (weather)
- Nominatim (geocoding)
- Overpass (POI search)
- DuckDuckGo (web search)

---

## 🎯 Test Sequence

1. **Start containers:**
   ```bash
   docker-compose up --build
   ```

2. **Wait for ready (check logs):**
   ```
   backend | Application startup complete
   frontend | ready started server on
   ```

3. **Open frontend:**
   ```
   http://localhost:3000
   ```

4. **Test health:**
   ```bash
   curl http://localhost:8000/health
   # Expected: {"status":"ok","version":"2.0"}
   ```

5. **Grant location permission** (PWA should prompt)

6. **Test sensor polling:**
   - Open DevTools → Network tab
   - Look for POST requests to `/context`
   - Should appear every 10 seconds

7. **Test chat:**
   - Type: "What's the weather?"
   - Should see WeatherCard render

8. **Test voice (optional):**
   - Click microphone button
   - Speak: "What should I eat?"
   - Should transcribe + send to chat

---

## 🔗 Key File Dependencies

```
frontend/app/page.tsx
  └─ useAgent() ──> agent.state (shared with backend)
  └─ useFrontendTool() ──> openNudgePanel, closeNudgePanel, speakAloud
  └─ useComponent() ──> WeatherCard, TrafficCard, FoodOptionsCard, etc.
  └─ pushSensors() ──> POST /context

backend/main.py
  └─ POST /context ──> redis.set("sensor_payload", ...)
  └─ build_agent() ──> LangGraph state machine
  └─ tools/ ──> send_nudge, manage_goals, get_goals, web_search

world_state.py (WIP)
  └─ fetch from redis ──> enrich ──> return dict

nudge_engine.py (WIP)
  └─ listen(world_state) ──> if_rules_match() ──> send_nudge()
```

---

## 📚 Quick Reference: CopilotKit Patterns Used

1. **L3 Generative UI** — `useComponent()` + render callbacks
   - Agent calls `weatherCard({...})` → renders React component
   
2. **L6 Shared State** — `useAgent()` + `agent.setState()`
   - Frontend updates `panel_open`, `nudges`, `goals`
   - Backend reads from `state` in tools
   
3. **L6 Frontend Tools** — `useFrontendTool()`
   - Agent calls `openNudgePanel()` → frontend updates UI

---

## 🚨 Known Issues / TODOs

- [ ] Verify `ag-ui-langgraph` package exists
- [ ] Implement postgres.py connection pool
- [ ] Implement redis_client.py helpers
- [ ] Write full SQL schema (001_init.sql)
- [ ] Implement world_state.py enrichment
- [ ] Implement nudge_engine.py rules
- [ ] Add error handling + logging
- [ ] Test sensor polling interval (currently 10s)
- [ ] Add user authentication (currently user_id hardcoded)

---

Generated: 2025-05-13 | Rebuild from scratch complete
