# JARVIS v3

Proactive personal AI. Context-aware. Relationship-intelligent.

## Stack

- **Frontend**: Next.js 14 PWA — chat, nudge panel, people directory, voice mode
- **Backend**: FastAPI + LangGraph ReAct agent — tools, world state, scheduler
- **DB**: Supabase PostgreSQL + pgvector
- **Auth**: Supabase Auth (JWT + Google OAuth)
- **AI**: OpenAI GPT-4o + text-embedding-3-small
- **Deploy**: PM2 + Caddy on VPS (no Docker)

## Local Development

### 1. Environment

```bash
cp .env.example .env
# Fill in: OPENAI_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
# Optional: GOOGLE_MAPS_API_KEY, OPENWEATHER_API_KEY

cp frontend/.env.local.example frontend/.env.local
# Fill in: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
# Set: NEXT_PUBLIC_JARVIS_URL=http://localhost:8000
```

### 2. Database migrations

Run these in order in your Supabase SQL Editor:

```
backend/db/migrations/001_core.sql
backend/db/migrations/002_relationships.sql
backend/db/migrations/003_rag.sql
backend/db/migrations/004_rls.sql
```

Then run this to allow general reminders (no person required):
```sql
ALTER TABLE public.relationship_events ALTER COLUMN person_id DROP NOT NULL;
```

### 3. Run locally

```bash
# Backend
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## VPS Deployment

```bash
# 1. Push to GitHub
git add . && git commit -m "update" && git push origin main

# 2. First-time VPS setup (run once)
ssh deploy@YOUR_VPS_IP
git clone https://github.com/YOUR_USERNAME/jarvis.git /home/deploy/apps/jarvis
sudo bash /home/deploy/apps/jarvis/deploy/setup-vps.sh
bash /home/deploy/apps/jarvis/deploy/install.sh
bash /home/deploy/apps/jarvis/deploy/start.sh
sudo cp /home/deploy/apps/jarvis/deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy

# 3. Upload env files (from local machine)
scp .env deploy@YOUR_VPS_IP:/home/deploy/apps/jarvis/.env
scp frontend/.env.local deploy@YOUR_VPS_IP:/home/deploy/apps/jarvis/frontend/.env.local

# 4. Future deploys (one command)
ssh deploy@YOUR_VPS_IP "bash /home/deploy/apps/jarvis/deploy/update.sh"
```

Set `NEXT_PUBLIC_JARVIS_URL=https://YOUR_VPS_IP.sslip.io/api` in the VPS frontend `.env.local`.

## Features

- **Chat**: Streaming LangGraph agent with tool use
- **World state**: Location, weather, time injected into every request
- **Reminders**: DB-backed, scheduler fires nudges every 5 minutes
- **Timers**: Client-side countdown, fires immediately with browser notification + speech
- **Voice**: OpenAI Realtime API (WebRTC) with Web Speech API fallback
- **Relationships**: Hybrid pgvector + keyword search over people and notes
- **Goals**: Track and manage personal goals
- **Nudges**: Proactive surface panel for reminders, birthdays, follow-ups
- **Scheduler**: APScheduler — events every 5min, birthdays at 8am, strength signals at midnight
