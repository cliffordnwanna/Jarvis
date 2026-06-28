# JARVIS v3 — Product Requirements Document
**The World's Best Personal AI**

Version 3.0 · June 2026 · Ecotronics Enterprise
Product Owner: Chukwuma Clifford Nwanna

---

## 1. Product Vision

JARVIS is not a chatbot. It is a proactive cognitive runtime — a personal AI that knows your world, remembers your people, and tells you what matters right now, without being asked.

The analogy is not Siri or Google Assistant. The analogy is JARVIS from Iron Man — an intelligence layer that runs continuously, understands context deeply, and surfaces what is relevant before you think to ask.

JARVIS v3 is built on two core pillars:

- **World Awareness** — real-time understanding of the environment around you: weather, location, time, calendar, traffic, and real-world context via Google APIs
- **Relationship Memory** — a persistent, intelligent layer that knows the people in your life, tracks interactions, remembers important details, and nudges you to be a better friend, colleague, and family member

These two pillars combine into one product: a single AI companion that understands your world and your people simultaneously, and helps you navigate both.

---

## 2. Problem Statement

### 2.1 The World Awareness Problem

Existing personal assistants are reactive — they answer when asked. They do not monitor your context continuously and surface what matters before you think to ask. By the time you remember to check the weather, you are already wet. By the time you check traffic, you are already late.

The gap: no personal AI maintains a continuously updated model of your real-world context and uses it to proactively improve your decisions.

### 2.2 The Relationship Memory Problem

Human relationships decay through neglect — not malice. People forget birthdays. They lose track of what a friend mentioned last month. They mean to follow up but the moment passes. They feel like bad friends and family members not because they do not care, but because they have no system.

Existing solutions are either too complex (CRM software designed for sales) or too shallow (phone calendar reminders with no context). No product treats personal relationships with the intelligence they deserve.

### 2.3 Why Now

LLMs can now understand natural language at human level. Persistent memory via vector databases is cheap and fast. Google APIs expose real-world context. Voice input is native on every device. The infrastructure exists — no one has assembled it correctly for personal use.

---

## 3. Target User

### 3.1 Primary User (v1)

Single user. The product owner. JARVIS v3 starts as a deeply personal tool — all configuration, memory, and context is built around one person. This is intentional. The product must work perfectly for one person before it scales.

### 3.2 Future User (v2 onwards)

Ambitious professionals, founders, and high-performers who manage complex lives — many relationships, many obligations, always in motion. They want leverage, not more apps to manage.

| Attribute | Value |
|---|---|
| Age range | 25 – 45 |
| Lifestyle | Mobile, high-context switching, relationship-driven |
| Pain | Forgetting people, missing moments, reacting instead of acting |
| Willingness to pay | High — this is a daily-use, high-value product |
| Platform | Mobile-first (phone), desktop secondary |

---

## 4. Design Principles

Every technical and product decision must pass these tests:

- **Proactive over reactive** — JARVIS speaks first. The user should not have to ask.
- **Speed over perfection** — a response in 1 second that is 80% right beats a perfect response in 5 seconds.
- **Natural input** — voice, text, or quick tap. No forms. No dropdowns. No friction.
- **Context-aware** — every response is shaped by the current world state and relationship context.
- **Privacy-first** — all personal data stays under the user's control. No third-party data selling.
- **Multi-device, no assumptions** — no battery level detection, no device-specific APIs that break on other platforms. Build for the browser universally.
- **Product-grade from day one** — architecture, database schema, and API design must support multi-user from the start, even if only one user exists initially.

---

## 5. System Architecture

### 5.1 Overview

JARVIS v3 is a three-tier system: a Next.js PWA frontend, a FastAPI backend with a LangGraph agent, and a PostgreSQL database hosted on Supabase with a Redis cache layer.

### 5.2 Component Map

| Component | Description |
|---|---|
| Frontend | Next.js 14 PWA — chat interface, nudge panel, people directory, voice input, generative UI cards |
| Backend | FastAPI + LangGraph ReAct agent — handles all AI reasoning, tool execution, and state management |
| LLM | OpenAI GPT-4o primary · Groq (llama-3.3-70b) fallback for speed-sensitive paths |
| Database | Supabase PostgreSQL — all persistent data: users, people, notes, events, goals, conversations |
| Cache | Upstash Redis — world state cache (TTL 300s), session data, nudge queue |
| AI Protocol | CopilotKit + AG-UI — bidirectional agent ↔ frontend state sync, generative UI cards |
| World Context | Google Maps API (geocoding, places, directions) · Open-Meteo (weather, free) · Google Calendar API |
| RAG | Supabase pgvector — semantic search over relationship notes, conversation history, user documents |
| Auth | Supabase Auth — email + Google OAuth, JWT sessions, row-level security on all tables |
| Deployment | Vercel (frontend) · Hetzner VPS or Railway (backend) · Upstash (Redis) · Supabase (DB) |

### 5.3 Data Flow

The system operates in two modes simultaneously:

- **Reactive mode** — user sends a message → LangGraph agent reads world state + relationship context → executes tools → returns response with optional generative UI card
- **Proactive mode** — world state changes (weather, time, calendar event) or relationship conditions trigger (birthday tomorrow, 30 days since last contact) → agent evaluates nudge rules → pushes nudge card to frontend without user prompt

---

## 6. World Awareness Module

### 6.1 Context Layers

| Feature | Priority | Notes |
|---|---|---|
| Time & date | P0 | Current time, timezone, day of week, local public holidays via Nager.Date |
| Location | P0 | GPS coordinates from browser → reverse geocoded via Google Maps Geocoding API |
| Weather | P0 | Open-Meteo (free, no key) — current conditions, hourly forecast, rain probability next 2 hours |
| Nearby places | P1 | Google Places API — restaurants, pharmacies, fuel stations, ATMs within walking/driving distance |
| Traffic & ETA | P1 | Google Directions API — commute time to saved locations (home, work) in current conditions |
| Calendar | P1 | Google Calendar API — events today and tomorrow, next meeting time, free slots |
| Goals | P0 | User-defined goals stored in DB — staleness tracking (days since last progress) |

### 6.2 Removed from v2

Battery level detection is removed. It relies on device-specific browser APIs that are inconsistent across platforms. JARVIS must work identically on any device — phone, tablet, laptop, or desktop.

### 6.3 Nudge Rules (World Layer)

- Rain probability > 60% within 2 hours and user is not at home → nudge: *"Rain likely at 3pm. Take an umbrella."*
- Next calendar event starts in < 20 minutes and traffic ETA > 15 minutes → nudge: *"Your 2pm meeting starts soon. Traffic is heavy — leave now."*
- Goal last touched > 7 days → nudge: *"You haven't made progress on [goal] in a week. Want to pick it up?"*
- No calendar events found for tomorrow morning → nudge: *"Your morning looks free tomorrow. Good time to plan deep work."*

---

## 7. Relationship Memory Module

### 7.1 Purpose

This module transforms JARVIS from a world-aware assistant into a socially intelligent one. It gives JARVIS the ability to know the people in the user's life — who they are, what matters to them, when they last connected, and what needs to happen next.

### 7.2 Core Concepts

| Concept | Definition |
|---|---|
| Person | Any human the user wants to track — friend, family, colleague, mentor, acquaintance |
| Note | A free-form memory attached to a person — captured via voice, text, or extracted from conversation |
| Event | A scheduled or logged interaction — birthday, follow-up reminder, meeting, call, occasion |
| Relationship strength | A computed signal (warm / cooling / cold) based on contact frequency and note recency |
| Circle | A grouping — inner circle, family, work, community — with different expected contact frequencies |

### 7.3 Feature Set

#### 7.3.1 People Vault (P0)
A searchable directory of people the user cares about. Each person has: name, relationship type, contact frequency goal, circle membership, last contact date, relationship strength signal, upcoming events, and a notes timeline.

#### 7.3.2 Voice and Text Notes (P0)
Primary input method for relationship data. User says or types anything about a person in natural language. JARVIS extracts structured facts automatically.

Example: *"Cherry just got a new job at a hospital in Abuja"* → JARVIS stores: `{person: Cherry, event: new_job, location: Abuja, note: "Started new hospital job in Abuja"}`

#### 7.3.3 Birthday and Occasion Reminders (P0)
Proactive nudges 7 days before, 2 days before, and on the day — each with a contextually appropriate message suggestion.

#### 7.3.4 Natural Language Calendar (P0)
*"Remind me to call Vincent next Thursday about the hardware project"* → JARVIS creates an event, links it to Vincent's profile, and fires a nudge at the right time with full context.

#### 7.3.5 Morning Nudge (P0)
Every morning at a configurable time, JARVIS sends a relationship briefing: who has a birthday soon, who is overdue for contact, who mentioned something important that deserves a follow-up today.

#### 7.3.6 Last Contact Tracker (P0)
Tracks the last time the user interacted with each person and surfaces people going cold based on circle expected contact frequency:
- Inner circle: 7 days
- Family: 14 days
- Work: 30 days
- Community: 60 days

#### 7.3.7 Message Suggestions (P0)
When a nudge fires or the user opens a person's profile, JARVIS generates a contextually appropriate first message based on what it knows: *"How's the new job in Abuja going, Cherry?"*

#### 7.3.8 Follow-up Threads (P1)
When JARVIS detects that someone mentioned something sensitive or significant, it automatically creates a follow-up reminder with full context attached.

#### 7.3.9 Ask Your Memory (P1)
*"What did Nnenna say about her business last month?"* → JARVIS queries the RAG layer and returns a specific answer from stored notes.

#### 7.3.10 Relationship Strength Score (P1)
Computed signal (warm / cooling / cold) per person. Based on: days since last contact, notes in last 30 days, follow-ups completed.

#### 7.3.11 Preference Memory (P2)
Stored interests, allergies, hobbies, preferences per person — used to personalise message suggestions and gift ideas.

#### 7.3.12 Monthly Relationship Review (P2)
An AI-written monthly summary card: how many people did you connect with, who did you neglect, which relationships improved.

---

## 8. Database Schema

All tables include row-level security (RLS) policies. Multi-user ready from day one.

### users
| Column | Type | Key | Description |
|---|---|---|---|
| id | uuid | PK | Supabase Auth user ID |
| display_name | text | | User's preferred name |
| timezone | text | | IANA timezone string e.g. Africa/Lagos |
| morning_nudge_time | time | | Time to deliver morning briefing (default 08:00) |
| home_lat / home_lng | float8 | | Saved home coordinates |
| work_lat / work_lng | float8 | | Saved work coordinates |
| created_at | timestamptz | | |
| updated_at | timestamptz | | |

### people
| Column | Type | Key | Description |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users | Owner of this person record |
| name | text | | Full name |
| relationship_type | text | | friend / family / colleague / mentor / acquaintance |
| circle | text | | inner / family / work / community |
| birthday | date | | Optional — used for birthday nudges |
| contact_frequency_days | int | | Target days between contacts |
| last_contacted_at | timestamptz | | Auto-updated on interaction log |
| strength_signal | text | | warm / cooling / cold — recomputed nightly |
| notes_summary | text | | AI-generated summary of all notes (refreshed weekly) |
| phone | text | | Optional |
| email | text | | Optional |
| tags | text[] | | Freeform tags for search |
| created_at | timestamptz | | |
| updated_at | timestamptz | | |

### relationship_notes
| Column | Type | Key | Description |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users | |
| person_id | uuid | FK → people | |
| content | text | | Raw note text as captured |
| extracted_facts | jsonb | | Structured facts extracted by LLM |
| embedding | vector(1536) | | OpenAI embedding for semantic search |
| source | text | | voice / text / chat_extraction / import |
| created_at | timestamptz | | |

### relationship_events
| Column | Type | Key | Description |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users | |
| person_id | uuid | FK → people | |
| event_type | text | | birthday / follow_up / call / meeting / occasion / check_in |
| title | text | | Human-readable label |
| scheduled_at | timestamptz | | When the event/reminder fires |
| completed_at | timestamptz | | Null if pending |
| nudge_sent | bool | | Whether nudge was delivered |
| context | jsonb | | {reason, note_id, message_suggestion} |
| created_at | timestamptz | | |

### interaction_log
| Column | Type | Key | Description |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users | |
| person_id | uuid | FK → people | |
| interaction_type | text | | call / message / in_person / note |
| notes | text | | Optional notes about the interaction |
| occurred_at | timestamptz | | When the interaction happened |
| created_at | timestamptz | | |

### goals
| Column | Type | Key | Description |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users | |
| title | text | | Goal description |
| status | text | | active / paused / completed |
| urgency | text | | low / medium / high |
| last_touched_at | timestamptz | | Last time user mentioned or updated this goal |
| created_at | timestamptz | | |

### nudge_history
| Column | Type | Key | Description |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users | |
| nudge_type | text | | weather / calendar / goal / relationship_birthday / relationship_followup / relationship_cooling |
| person_id | uuid | FK → people (nullable) | Set for relationship nudges |
| message | text | | The nudge text delivered |
| priority | text | | low / medium / high |
| delivered_at | timestamptz | | |
| dismissed_at | timestamptz | | Null until user dismisses |
| actioned | bool | | Did user act on it |

### conversations
| Column | Type | Key | Description |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users | |
| title | text | | Auto-generated from first message |
| created_at | timestamptz | | |
| last_message_at | timestamptz | | |

### messages
| Column | Type | Key | Description |
|---|---|---|---|
| id | uuid | PK | |
| conversation_id | uuid | FK → conversations | |
| user_id | uuid | FK → users | |
| role | text | | user / assistant / tool |
| content | text | | |
| meta | jsonb | | Tool call metadata, card type, people mentioned |
| created_at | timestamptz | | |

### rag_documents
| Column | Type | Key | Description |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users | |
| source | text | | system_prompt / user_profile / relationship_note / goal |
| content | text | | |
| embedding | vector(1536) | | text-embedding-3-small |
| created_at | timestamptz | | |

---

## 9. API Endpoints

All endpoints except `/health` require a valid Supabase JWT in the Authorization header.

### 9.1 Core
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /health | None | Health check |
| GET | /world-state | JWT | Latest cached world state |
| POST | /context | JWT | Enrich sensors → cache → evaluate nudges |

### 9.2 Nudges
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /nudges | JWT | List all pending nudges |
| DELETE | /nudges/{id} | JWT | Dismiss a single nudge |
| DELETE | /nudges | JWT | Dismiss all nudges |
| POST | /nudges/{id}/action | JWT | Mark nudge as actioned |

### 9.3 People & Relationships
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /people | JWT | List all people — supports ?circle=inner&strength=cooling |
| POST | /people | JWT | Create a new person |
| GET | /people/{id} | JWT | Full person profile with notes and events |
| PATCH | /people/{id} | JWT | Update person fields |
| DELETE | /people/{id} | JWT | Soft-delete |
| GET | /people/{id}/notes | JWT | List relationship notes |
| POST | /people/{id}/notes | JWT | Add note — triggers LLM extraction |
| GET | /people/{id}/events | JWT | List upcoming events |
| POST | /people/{id}/events | JWT | Create event or follow-up reminder |
| POST | /people/{id}/log | JWT | Log an interaction — updates last_contacted_at |
| GET | /people/suggest-message/{id} | JWT | Generate context-aware message suggestion |
| GET | /people/overdue | JWT | List people past contact frequency target |
| POST | /people/search | JWT | Semantic search across all relationship notes |

### 9.4 Goals
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /goals | JWT | List all goals |
| POST | /goals | JWT | Create a goal |
| PATCH | /goals/{id} | JWT | Update status or urgency |
| DELETE | /goals/{id} | JWT | Archive a goal |
| POST | /goals/{id}/touch | JWT | Mark goal as worked on today |

### 9.5 Memory
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /memory/conversations | JWT | List conversation history |
| GET | /memory/conversations/{id} | JWT | Full conversation with messages |
| DELETE | /memory/conversations/{id} | JWT | Delete a conversation |
| POST | /memory/search | JWT | Semantic search across conversation history |

### 9.6 Agent
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /agent | JWT | CopilotKit LangGraph endpoint |

---

## 10. Frontend Architecture

### 10.1 Pages

| Page | Description |
|---|---|
| / (Home) | Chat interface with NudgePanel sidebar |
| /people | People directory — searchable with strength signals |
| /people/[id] | Person profile — notes timeline, events, message suggestion |
| /people/new | Add a new person |
| /calendar | 30-day view combining relationship events and world calendar |
| /goals | Goal tracker with staleness indicators |
| /settings | Profile, home/work location, morning nudge time, calendars |

### 10.2 Generative UI Cards

| Card | Description |
|---|---|
| WeatherCard | Current conditions + 3-hour forecast + rain alert |
| TrafficCard | ETA to home/work + congestion + alternate route |
| PlacesCard | Nearby restaurants/services with distance and Google Maps link |
| GoalReminderCard | Stale goal nudge with one-tap "worked on it today" action |
| PersonCard | Person profile summary with last contact and message button |
| RelationshipNudgeCard | Birthday / follow-up / cooling alert with suggested message |
| MorningBriefCard | Daily relationship briefing |
| CalendarCard | Today's and tomorrow's events with free slot detection |

### 10.3 Voice Input

Web Speech API for voice-to-text on Chrome and Safari. Transcribed text is sent to the agent exactly as typed text would be. Voice notes for people profiles captured the same way — tap mic on person profile, speak, note is saved and processed.

---

## 11. Agent System Prompt (Summary)

The LangGraph agent operates with a structured system prompt covering:

- **Identity** — JARVIS is a proactive personal AI, not a chatbot. It surfaces what matters without being asked.
- **World state reading** — before every response, reads the current world state and uses it to colour the response.
- **Relationship awareness** — checks if any people are mentioned, retrieves their profile and recent notes, incorporates this into the response.
- **Reactive mode** — answer directly, use world state as context, render a card if the response is visual, keep responses concise.
- **Proactive mode** — evaluate nudge conditions on every context update, send nudges without being asked, suppress low-priority nudges during likely focus time.
- **Communication style** — direct, warm, intelligent. No filler. No "As an AI..." disclaimers. Speak like the world's most capable colleague.

---

## 12. MVP Scope and Phasing

### Phase 1 — Core (Build First, weeks 1–4)

| Feature | Priority | Notes |
|---|---|---|
| Supabase Auth (email + Google) | P0 | Gate everything behind auth from day one |
| Database migrations (all tables) | P0 | Full schema including people and relationships |
| World state engine (time, location, weather) | P0 | Google Maps geocoding + Open-Meteo |
| Nudge engine (weather, calendar, goals) | P0 | Basic rule set, fires proactively |
| Chat interface + generative UI cards | P0 | CopilotKit + LangGraph — reactive Q&A |
| People vault + person profiles | P0 | CRUD, circle assignment, last contact tracking |
| Voice and text notes for people | P0 | LLM extraction from freeform input |
| Birthday reminders | P0 | 7-day, 2-day, day-of nudges with message suggestions |
| Morning nudge | P0 | Daily relationship briefing at configurable time |
| Natural language calendar | P0 | Text/voice → event creation linked to person profile |
| Goal tracking | P0 | Create, update, staleness nudges |
| Deploy to Vercel + Hetzner/Railway | P0 | Working URL for daily personal use |

### Phase 2 — Intelligence (weeks 5–8)

| Feature | Priority | Notes |
|---|---|---|
| Google Calendar two-way sync | P1 | Real events, real free/busy context |
| Google Places nearby search | P1 | Restaurants, services by current location |
| Google Directions traffic ETA | P1 | Commute nudges based on real traffic |
| Semantic search over notes (RAG) | P1 | "What did Cherry say about X?" — vector search |
| Follow-up thread auto-creation | P1 | LLM detects sensitive mentions, creates follow-ups |
| Relationship strength scoring | P1 | Computed nightly, drives nudge priority |
| People import from contacts | P1 | CSV or vCard import for bulk onboarding |
| Ask your memory (chat) | P1 | Natural language query over all relationship data |
| Conversation history + search | P1 | Persistent chat history, searchable |

### Phase 3 — Product (weeks 9–12)

| Feature | Priority | Notes |
|---|---|---|
| Multi-user with proper RLS | P2 | Already designed in schema — needs testing at scale |
| Preference memory per person | P2 | Interests, allergies, hobbies |
| Monthly relationship review | P2 | AI-written monthly summary card |
| WhatsApp send integration | P2 | One-tap to send suggested message |
| Shared circles (family/couples) | P2 | "We" haven't called Grandma — shared layer |
| Mobile app (Expo) | P2 | PWA first, native later |
| Waitlist and onboarding flow | P2 | Before opening to other users |

---

## 13. Tech Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 · TypeScript · Tailwind CSS · CopilotKit ^1.57 · shadcn/ui |
| Backend | Python 3.11 · FastAPI · LangGraph · LangChain · Pydantic v2 |
| LLM (primary) | OpenAI GPT-4o |
| LLM (fast path) | Groq llama-3.3-70b |
| Embeddings | OpenAI text-embedding-3-small |
| Database | Supabase PostgreSQL + pgvector |
| Cache | Upstash Redis — TTL 300s |
| Auth | Supabase Auth — JWT, Google OAuth, RLS |
| Maps & Places | Google Maps Platform — Geocoding, Places, Directions APIs |
| Weather | Open-Meteo — free, no key required |
| Calendar | Google Calendar API — OAuth 2.0 |
| AI Protocol | CopilotKit + AG-UI |
| Frontend deploy | Vercel |
| Backend deploy | Hetzner VPS (existing) or Railway |
| Monitoring | Sentry (errors) · Vercel Analytics |

---

## 14. Explicit Exclusions

These are intentionally out of scope for v3:

- **Battery level detection** — removed. Device-specific, unreliable across platforms.
- **Meal logging and hunger prediction** — distraction. Can be added post-v3.
- **Pattern learning / behavioral ML** — premature. Needs months of data first.
- **Native mobile app** — PWA is sufficient. Build after web product is validated.
- **Push notifications** — PWA service worker notifications unreliable on iOS. Use in-app nudge panel.
- **Social features** — JARVIS is personal and private.
- **Marketplace or third-party integrations** — keep the surface small and reliable in v3.

---

## 15. Success Metrics

### Phase 1 (personal use)
- Daily active use — you open JARVIS at least once per day without being prompted
- Nudge accuracy — > 80% of nudges feel relevant when they fire
- Relationship coverage — > 80% of important people in your life have a profile with at least one note
- Zero missed birthdays — for people with birthdays stored
- Morning nudge opens — you open the morning briefing on > 5 days per week

### Phase 3 (product)
- 100 paying users within 3 months of opening
- < 5% monthly churn

---

## 16. Next Steps — Build Sequence

1. Archive current v2 codebase in `/archive/v2/` — keep everything, reference freely
2. Set up new GitHub repo: `jarvis-v3` (or work in same repo with clean structure)
3. Scaffold backend: FastAPI + Supabase Auth + all DB migrations
4. Scaffold frontend: Next.js + CopilotKit + Supabase Auth UI
5. Build world state engine with Google Maps + Open-Meteo
6. Build relationship module: people CRUD + notes + events
7. Wire LangGraph agent with all tools
8. Build nudge engine (world + relationship rules)
9. Build frontend pages: home, /people, /people/[id], /calendar
10. Deploy to Vercel + Hetzner. Use daily.
11. Iterate based on daily use. Fix what hurts. Add Phase 2 features.

---

*JARVIS v3 — Build what you wish existed. Use it every day. Make it irreplaceable.*

*Ecotronics Enterprise · Private & Confidential*
