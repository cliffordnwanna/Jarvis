# JARVIS v3

Proactive personal AI. Context-aware. Relationship-intelligent.

**Live:** https://89.167.93.25.sslip.io

## Stack

- **Frontend**: Next.js 14 PWA — chat, nudge panel, people directory, voice mode
- **Backend**: FastAPI + LangGraph ReAct agent (GPT-4o), Python 3.12
- **Voice**: LiveKit + OpenAI Whisper STT + GPT-4o-mini + TTS
- **DB**: Supabase PostgreSQL + pgvector
- **Auth**: Supabase Auth (JWT + Google OAuth)
- **Maps**: TomTom APIs — places search, routing, real Lagos traffic
- **Deploy**: PM2 + Caddy on VPS at 89.167.93.25 (no Docker)

## Features

- **Chat**: Streaming LangGraph agent with tool use
- **Voice**: LiveKit voice agent — full parity with text (places, directions, traffic, reminders, people, goals)
- **World state**: Location, weather, time injected into every request
- **Maps**: Find nearby places, get traffic-aware directions anywhere in Lagos
- **Reminders**: DB-backed, scheduler fires nudges every 5 minutes
- **Timers**: Client-side countdown with browser notification
- **Relationships**: Hybrid pgvector + keyword search over people and notes
- **Goals**: Track and manage personal goals
- **Nudges**: Proactive surface panel for reminders, birthdays, follow-ups
- **Scheduler**: APScheduler — events every 5min, birthdays at 8am, strength signals at midnight
- **Multi-user**: Onboarding tour for new users, per-user data isolation, rate limiting

## Local Development

### 1. Environment

```bash
cp .env.example .env
# Required: OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
# Required: TOMTOM_API_KEY (free at developer.tomtom.com — no card required)
# Optional: TAVILY_API_KEY, OPENWEATHER_API_KEY
# Optional: LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL (for voice)

cp frontend/.env.local.example frontend/.env.local
# Required: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
# Set: NEXT_PUBLIC_JARVIS_URL=http://localhost:8000
```

### 2. Database migrations

Run in order in your Supabase SQL Editor:

```
backend/db/migrations/001_core.sql
backend/db/migrations/002_relationships.sql
backend/db/migrations/003_rag.sql
backend/db/migrations/004_rls.sql
```

Then run these fixes:
```sql
-- Allow reminders without a linked person
ALTER TABLE public.relationship_events ALTER COLUMN person_id DROP NOT NULL;

-- TomTom usage tracking
CREATE TABLE IF NOT EXISTS public.api_usage (
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  date date NOT NULL DEFAULT CURRENT_DATE,
  tomtom_calls int NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, date)
);

CREATE OR REPLACE FUNCTION increment_tomtom_usage(p_user_id uuid, p_date date)
RETURNS void AS $$
BEGIN
  INSERT INTO public.api_usage (user_id, date, tomtom_calls)
  VALUES (p_user_id, p_date, 1)
  ON CONFLICT (user_id, date)
  DO UPDATE SET tomtom_calls = api_usage.tomtom_calls + 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 3. Run locally

```bash
# Backend
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev

# Voice agent (separate terminal, optional)
cd /path/to/jarvis
python -m backend.livekit_agent
```

Open http://localhost:3000

## VPS Deployment

```bash
# 1. Push to GitHub
git add . && git commit -m "update" && git push origin main

# 2. SSH to VPS and deploy
ssh deploy@89.167.93.25
cd /home/deploy/apps/jarvis && git pull

# Restart backend
pm2 restart jarvis-backend

# Restart frontend (after UI changes)
cd frontend && npm run build && pm2 restart jarvis-frontend

# Restart voice agent (after livekit_agent.py changes)
pm2 restart jarvis-voice

# Check logs
pm2 logs jarvis-backend --lines 50 --nostream
pm2 logs jarvis-voice --lines 50 --nostream
```

## Architecture notes

- `user_id` always comes from validated JWT (`get_current_user()`), never from request body
- `SUPABASE_SERVICE_ROLE_KEY` is backend-only — never in frontend
- World state cached in Supabase `world_state` table (TTL 300s) — no Redis
- TomTom rate limit: 80 calls/user/day tracked in `api_usage` table
- Voice agent builds full user context (name, home, work, people, goals, reminders) on session start
- Text agent gets same context injected per-request in `main.py`
- Sentinel pattern: `__TIMER__:seconds:label`, `__MAP_PLACES__:[...]`, `__MAP_ROUTE__:{...}` — frontend strips and renders as widgets
