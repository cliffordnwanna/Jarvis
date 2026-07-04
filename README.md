# JARVIS

> Your Personal AI Operating System

[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-green)](https://supabase.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent-purple)](https://www.langchain.com/langgraph)
[![LiveKit](https://img.shields.io/badge/Voice-LiveKit-orange)](https://livekit.io/)

> An AI operating system designed to understand your world, not just your prompts.

JARVIS is an experimental personal AI platform that combines persistent memory, real-time world awareness, voice interaction, relationship intelligence and autonomous reasoning into a single system.

Unlike traditional AI assistants that wait for instructions, JARVIS continuously maintains context about the user’s environment, remembers what matters, and proactively helps with planning, organization and decision-making.

**Live:** https://89.167.93.25.sslip.io

## Why I Built JARVIS

Modern AI assistants are remarkably capable, yet they remain fundamentally reactive. They wait for users to ask questions before providing assistance, often without awareness of the user’s location, current environment, relationships, goals, schedule or changing circumstances.

I wanted to explore a different approach.

JARVIS was built to answer one question:

> What if an AI assistant continuously understood your world and helped before you even asked?

Instead of relying solely on conversation history, JARVIS combines structured memory, environmental awareness and intelligent reasoning to deliver assistance that is timely, contextual and genuinely personal.

## Core Design Principles

### Context First

Recommendations improve dramatically when AI understands the user’s current environment. Every interaction incorporates relevant context such as current location, weather, local time, traffic conditions, active goals and personal relationships.

### Persistent Memory

Conversations should not disappear. JARVIS maintains structured long-term memory that belongs entirely to the user. Memories remain searchable, editable and extensible rather than being hidden inside opaque chat history.

### Proactive Intelligence

Rather than waiting for prompts, JARVIS continuously identifies opportunities to help. Examples include reminder nudges, birthday notifications, follow-up suggestions, daily planning and goal tracking.

### Privacy by Design

User memories remain under user control. The architecture was intentionally designed around a dedicated database rather than opaque conversational memory, making behaviour easier to inspect, debug and extend.

### Modular Architecture

Every major capability is independently replaceable. Large language models, search providers, memory systems, voice services and mapping providers can evolve without redesigning the entire platform.

## System Architecture

```text
                     User
                       │
       ┌───────────────┼────────────────┐
       │               │                │
    Web Chat        Voice Mode      Mobile PWA
       │               │
       └────── Next.js Frontend ───────┘
                     │
                FastAPI Backend
                     │
      ┌──────────────┼──────────────┐
      │              │              │
  LangGraph      Memory Layer    Tool Layer
      │              │              │
      │          Supabase       Tavily Search
      │          pgvector       TomTom Maps
      │          PostgreSQL     Weather APIs
      │
   OpenAI Models
```

### Architecture Notes

- `user_id` always comes from validated JWT, never from request data.
- World state is cached and reused to reduce latency.
- No Redis is used; state is stored in Supabase.
- APScheduler powers proactive reminders and scheduled events.
- Voice and text share the same reasoning layer.
- The frontend renders structured tool outputs through a sentinel-based pattern.
- Rate limiting is applied at the API layer.

## Key Capabilities

### AI Conversation

- Streaming conversations
- LangGraph reasoning agent
- Tool calling
- Context injection

### Persistent Memory

- Long-term memory
- Relationship management
- Goal tracking
- Reminder storage
- Vector search

### Voice Assistant

- LiveKit voice sessions
- Whisper speech recognition
- Natural speech synthesis
- Shared reasoning engine

### World Awareness

JARVIS continuously enriches conversations using:

- Current location
- Weather
- Local time
- Traffic
- Nearby places
- Route planning

### Relationship Intelligence

Unlike traditional assistants, JARVIS remembers people. It stores relationships, important dates, notes, follow-ups and birthdays, allowing conversations to become increasingly personal over time.

### Proactive Assistance

Rather than simply answering questions, JARVIS actively assists by generating smart reminders, daily nudges, goal reviews, birthday alerts and follow-up suggestions.

## Technology Stack

### Frontend

- Next.js 14
- React
- TypeScript
- Tailwind CSS
- PWA

### Backend

- FastAPI
- Python 3.12
- LangGraph
- OpenAI models

### Voice

- LiveKit
- Whisper
- OpenAI TTS

### Database and Auth

- Supabase PostgreSQL
- pgvector
- Supabase Auth
- JWT
- Google OAuth

### Maps and Search

- TomTom APIs
- Tavily

### Deployment

- PM2
- Caddy
- Ubuntu VPS
- No Docker

## Engineering Challenges

Some of the most interesting engineering problems solved during development included:

- Maintaining accurate real-world context using multiple free-tier APIs.
- Designing persistent user memory that is private, extensible and easy to debug.
- Sharing the same reasoning engine across both voice and text interactions.
- Synchronizing reminders and scheduled events with background workers.
- Injecting contextual information without overwhelming the language model.
- Building a modular architecture that can accommodate future LLMs and tools.

## Repository Structure

```text
backend/
  agent.py
  auth.py
  main.py
  scheduler.py
  world_state.py
  db/
  routers/
  tools/
frontend/
  app/
  components/
  lib/
  public/
rag/
  seed.py
  system_prompt.md
deploy/
  Caddyfile
  install.sh
  start.sh
  update.sh
  setup-vps.sh
```

## Roadmap

| Capability | Status |
| --- | --- |
| Persistent Memory | Completed |
| Voice Conversations | Completed |
| Relationship Intelligence | Completed |
| Context Awareness | Completed |
| Goal Management | Completed |
| Reminder Engine | Completed |
| Web Search | Completed |
| Multi-LLM Routing | Planned |
| MCP Integration | Planned |
| Document Search | Planned |
| Code Execution | Planned |
| Computer Control | Planned |

## Project Gallery

Screenshots and architecture visuals will be added here as the product matures.

- Dashboard
- Voice Mode
- Memory System
- Goal Tracking
- Relationship Management
- World Context
- Architecture Diagram

## Lessons Learned

JARVIS taught me that building useful AI systems is less about selecting the best language model and more about engineering the ecosystem around it. Memory, context, tools, scheduling, user modelling and real-world awareness contribute just as much to perceived intelligence as the model itself.

This project continues to evolve as a long-term exploration into what a truly personal AI operating system could become.

## Installation

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

```sql
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

## Deployment

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
