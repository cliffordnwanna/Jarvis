# JARVIS — Production Deployment & Expansion Guide

Complete end-to-end reference. Follow phases in order.

---

## Architecture

```
Your Browser
  │
  ├─── Chat messages ──► Vercel (Next.js frontend)
  │                            │
  │                            └── POST /llm/chat/completions ──► Hetzner VPS (FastAPI)
  │                                                                      │
  │                                                                      ├── OpenAI (LLM: gpt-4o-mini)
  │                                                                      ├── OpenAI (embeddings: text-embedding-3-small)
  │                                                                      ├── Supabase (RAG storage + pgvector)
  │                                                                      ├── Redis (world state, nudges)
  │                                                                      └── Postgres (goals)
  │
  └─── POST /context (sensors) ──► Hetzner VPS (FastAPI)
  └─── GET  /nudges            ──► Hetzner VPS (FastAPI)
```

**Why this order matters:**

| Phase | What | Why first |
|---|---|---|
| **Phase 4** | Cloud deploy (Hetzner + Vercel) | Everything else requires always-on infrastructure |
| **Phase 3** | Telegram bot | Works 24/7 only after cloud deploy |
| **Phase 1** | Self-learning memory | Needs a running backend to persist answers |
| **Phase 2** | Google Calendar | Schedule intelligence depends on stable infra |

---

## Phase 4 — Cloud Deploy

### 4.1 Pre-flight: Commit Everything Locally

The backend/, frontend/, and rag/ directories must be committed before pushing to GitHub.

```powershell
# From repo root on your Windows machine
git add backend/ frontend/ rag/ docker-compose.yml docker-compose.prod.yml Dockerfile docs/
git status  # verify everything you expect is staged
git commit -m "Production-ready JARVIS: FastAPI + Next.js + RAG + world state"
git push origin main
```

Verify on GitHub that all directories appear before continuing.

---

### 4.2 Hetzner VPS Prerequisites

SSH into your Hetzner VPS (use the `deploy` user if that's what Hetzner created):

```bash
ssh deploy@YOUR_HETZNER_IP
```

**Check your CPU architecture — this affects which binaries to download:**

```bash
dpkg --print-architecture
# arm64  → Hetzner Ampere/ARM servers (CAX series)
# amd64  → Hetzner standard x86 servers (CX/CPX series)
```

**Install Docker (if not installed):**

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
docker --version   # confirm
```

**Add your user to the docker group (run docker without sudo):**

```bash
sudo usermod -aG docker $USER
newgrp docker        # apply immediately without re-login
docker ps            # should work without sudo
```

**Install Git:**

```bash
sudo apt install -y git
```

**Install cloudflared (architecture-aware):**

```bash
ARCH=$(dpkg --print-architecture)   # arm64 or amd64
sudo curl -L "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}" \
  -o /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared
cloudflared --version   # confirm
```

---

### 4.3 Clone Repo on VPS

```bash
sudo mkdir -p /var/www/jarvis
sudo chown $USER:$USER /var/www/jarvis
cd /var/www/jarvis
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git .
```

Verify the structure:

```bash
ls -la
# Expected: backend/  frontend/  rag/  docker-compose.prod.yml  Dockerfile  docs/
```

---

### 4.4 Create Production .env on VPS

```bash
nano /var/www/jarvis/.env
```

Paste and fill in every value:

```env
# OpenAI — LLM completions (gpt-4o-mini) + RAG embeddings (text-embedding-3-small)
OPENAI_API_KEY=your_openai_key_here

# Supabase (RAG storage)
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# RAG settings
RAG_ENABLED=true
RAG_SIMILARITY_THRESHOLD=0.2
RAG_MIN_SIMILARITY=0.40
RAG_USER_ID=default
RAG_TOP_K=5
RAG_MAX_CONTEXT_CHARS=2000
RAG_CHUNK_TARGET_CHARS=600

# Embeddings
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536

# Redis — docker-compose overrides this to redis://redis:6379 inside containers
REDIS_URL=redis://localhost:6380

# Postgres — docker-compose overrides this to postgresql://jarvis:jarvis@postgres:5432/jarvis
DATABASE_URL=postgresql://jarvis:jarvis@localhost:5433/jarvis

# Timezone
DEFAULT_TIMEZONE=Africa/Lagos

# Telegram (fill in Phase 3)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Google Calendar (fill in Phase 2)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
```

Save with `Ctrl+O`, `Enter`, `Ctrl+X`.

**Verify the file is NOT empty:**

```bash
grep OPENAI /var/www/jarvis/.env
# Should print: OPENAI_API_KEY=sk-...
```

---

### 4.5 Build and Start the Backend

```bash
cd /var/www/jarvis
docker compose -p jarvis -f docker-compose.prod.yml up -d --build
```

This starts three containers: `jarvis-postgres-1`, `jarvis-redis-1`, `jarvis-backend-1`.

> The `-p jarvis` flag sets the project name. This avoids conflicts with UpJobs containers.

**Watch the startup logs:**

```bash
docker compose -p jarvis -f docker-compose.prod.yml logs -f backend
```

Expected output:
```
INFO:     Application startup complete.
CopilotKit /agent endpoint mounted.
```

If CopilotKit fails to mount, the backend still works — REST endpoints function regardless.

**Verify the backend is responding:**

```bash
curl http://localhost:8001/health
# Expected: {"status":"ok","version":"2.0"}
```

**Check all containers are healthy:**

```bash
docker compose -p jarvis -f docker-compose.prod.yml ps
# All three services should show "healthy" or "running"
```

---

### 4.6 Set Up HTTPS with Caddy

You need a domain name pointing to your Hetzner IP. Options:

**Option A — Use a subdomain of an existing domain (recommended):**
Add a DNS A record in your domain registrar:
```
Type: A
Name: jarvis    (or api.jarvis, etc.)
Value: YOUR_HETZNER_IP
TTL: 300
```
Wait 2–5 minutes for DNS to propagate. Verify with: `ping jarvis.yourdomain.com`

**Option B — Buy a new domain (~$10/year):**
Namecheap, Cloudflare Registrar, or Google Domains. Point the root or a subdomain to your Hetzner IP.

**Option C — Free HTTPS with Cloudflare Tunnel (no domain purchase needed if you already have one in Cloudflare):**

> cloudflared was already installed in step 4.2. Your server is ARM64 — that install command handled it.

```bash
# Step 1: Login — prints a URL, copy it and open in your Windows browser
cloudflared tunnel login
# After you authorise in browser, a cert is saved to ~/.cloudflared/cert.pem

# Step 2: Create the tunnel (creates a UUID-named tunnel)
cloudflared tunnel create jarvis-backend
# Output: "Created tunnel jarvis-backend with id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
# Copy that UUID — you need it in the config

# Step 3: Create config file
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Paste this into config.yml (replace `YOUR_TUNNEL_UUID` and `YOUR_DOMAIN`):

```yaml
tunnel: YOUR_TUNNEL_UUID
credentials-file: /home/deploy/.cloudflared/YOUR_TUNNEL_UUID.json

ingress:
  - hostname: jarvis-api.YOUR_DOMAIN.com
    service: http://localhost:8001
  - service: http_status:404
```

> Replace `deploy` with your actual username if different. The credentials file is auto-created in `~/.cloudflared/` during `tunnel create`.

```bash
# Step 4: Add DNS record (points jarvis-api.yourdomain.com → tunnel)
cloudflared tunnel route dns jarvis-backend jarvis-api.YOUR_DOMAIN.com

# Step 5: Install as a system service so it runs on boot
sudo cloudflared service install
# This reads ~/.cloudflared/config.yml and creates a systemd service

sudo systemctl start cloudflared
sudo systemctl enable cloudflared
sudo systemctl status cloudflared   # should show "active (running)"
```

Test the tunnel is routing correctly:
```bash
curl https://jarvis-api.YOUR_DOMAIN.com/health
# Expected: {"status":"ok","version":"2.0"}
```

> If you don't have a domain: Cloudflare offers free `*.trycloudflare.com` subdomains for quick testing via `cloudflared tunnel --url http://localhost:8001`. But for production, use a real domain — Cloudflare Registrar has .com domains for ~$10/year at cost price.

---

**After DNS is pointing to your Hetzner IP — configure Caddy:**

```bash
nano /etc/caddy/Caddyfile
```

Replace the entire file with:

```
jarvis.yourdomain.com {
    reverse_proxy localhost:8001
}
```

> Replace `jarvis.yourdomain.com` with your actual domain/subdomain.

```bash
systemctl reload caddy
```

Caddy automatically fetches a Let's Encrypt TLS certificate. Check it worked:

```bash
curl https://jarvis.yourdomain.com/health
# Expected: {"status":"ok","version":"2.0"}
```

If it returns HTTPS, the backend is live and secure.

---

### 4.7 Deploy Frontend to Vercel

Vercel hosts Next.js apps for free with global CDN.

**Step 1 — Create a Vercel account:**
Go to [vercel.com](https://vercel.com), sign in with GitHub.

**Step 2 — Import the repo:**
- Click "Add New Project"
- Select your GitHub repo (jarvis)
- Vercel detects Next.js automatically

**Step 3 — Configure the root directory:**
Before clicking Deploy, change:
- **Root Directory:** `frontend`
- (This tells Vercel to build from the `frontend/` subfolder, not the repo root)

**Step 4 — Set environment variables:**
In the Vercel project settings → Environment Variables, add:

```
Name:  NEXT_PUBLIC_JARVIS_URL
Value: https://jarvis.yourdomain.com
```

> This must be the HTTPS URL from step 4.6. Never use `http://` here — the browser blocks mixed content from an HTTPS frontend.

**Step 5 — Deploy:**
Click "Deploy". Build takes 2–3 minutes. Vercel gives you a URL like `jarvis-frontend.vercel.app`.

**Step 6 — Set your custom domain (optional):**
In Vercel project → Domains → Add domain (e.g., `jarvis.app` or `ai.yourdomain.com`).

---

### 4.8 Post-Deploy Verification Checklist

Run through every item before declaring deploy complete.

**Backend checks (from your browser or Postman):**

```
GET  https://jarvis.yourdomain.com/health
     → {"status":"ok","version":"2.0"}

GET  https://jarvis.yourdomain.com/world-state
     → {"status":"empty","message":"No world state yet — POST to /context first"}
     (empty is fine — frontend will populate it)

GET  https://jarvis.yourdomain.com/nudges
     → []
```

**Frontend checks (open your Vercel URL in browser):**

- [ ] Page loads with dark background, JARVIS header
- [ ] Browser prompts for location permission → Allow
- [ ] Status chips appear after ~10 seconds (City, Weather, Temp, etc.)
- [ ] Chat: type "Hello JARVIS, what time is it?" → AI responds as JARVIS
- [ ] Chat: type "What is my battery level?" → AI reads device.battery_pct from world state
- [ ] Chat: type "Show me the weather" → AI calls weatherCard and renders a card
- [ ] Nudges button appears in header (may show 0 until nudges are triggered)

**RAG check:**

```
POST https://jarvis.yourdomain.com/llm/chat/completions
Content-Type: application/json

{
  "model": "llama-3.3-70b-versatile",
  "messages": [{"role": "user", "content": "What is Clifford's full name?"}]
}
```

Expected: response mentions "Chukwuma Clifford Nwanna" (pulled from RAG).

---

### 4.9 Keeping the VPS Updated

Every time you push new code to GitHub:

```bash
ssh root@YOUR_HETZNER_IP
cd /var/www/jarvis
git pull origin main
docker compose -p jarvis -f docker-compose.prod.yml up -d --build
```

The `--build` flag rebuilds the backend image. Postgres data persists in the Docker volume.

**Useful maintenance commands:**

```bash
# View live backend logs
docker compose -p jarvis -f docker-compose.prod.yml logs -f backend

# Restart just the backend (after code change)
docker compose -p jarvis -f docker-compose.prod.yml restart backend

# Stop everything
docker compose -p jarvis -f docker-compose.prod.yml down

# Stop and wipe data (nuclear)
docker compose -p jarvis -f docker-compose.prod.yml down -v

# Shell into running backend container
docker exec -it jarvis-backend-1 bash

# Check Redis directly
docker exec -it jarvis-redis-1 redis-cli ping
```

---

## Phase 3 — Telegram Bot

**Why Telegram before Calendar:** You want JARVIS to reach you at 6:30am without opening the browser. Telegram is the wire. Calendar is the content.

### 3.1 Create Your Telegram Bot

1. Open Telegram. Search for `@BotFather`.
2. Send: `/newbot`
3. Follow prompts:
   - Bot name: `JARVIS`
   - Username: `jarvis_YOUR_NAME_bot` (must be unique globally, must end in `bot`)
4. BotFather replies with your **BOT_TOKEN**. Copy it. Format: `7123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`

**Get your Chat ID:**

1. Start a chat with your new bot (click the link BotFather provides).
2. Send any message (e.g., "hello").
3. Open in browser:
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Find `"chat":{"id":123456789}` in the response. That number is your **CHAT_ID**.

**Add to .env on both your local machine and Hetzner VPS:**

```env
TELEGRAM_BOT_TOKEN=7123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
TELEGRAM_CHAT_ID=123456789
```

---

### 3.2 Install APScheduler

Add to `backend/requirements.txt`:

```
apscheduler
pytz
```

---

### 3.3 Create Telegram Notifier

Create `backend/telegram_notify.py`:

```python
from __future__ import annotations
import os
import httpx


async def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        })
```

---

### 3.4 Create Scheduler with Morning/Evening Briefings

Create `backend/scheduler.py`:

```python
from __future__ import annotations
import json
import os
import redis.asyncio as aioredis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from backend.telegram_notify import send_telegram

scheduler = AsyncIOScheduler()
LAGOS_TZ = pytz.timezone("Africa/Lagos")


async def morning_briefing():
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    try:
        raw = await r.get("world_state")
        ws = json.loads(raw) if raw else {}
    finally:
        await r.aclose()

    temp = ws.get("environment", {}).get("weather", {}).get("temp_c")
    weather = ws.get("environment", {}).get("weather", {}).get("description", "")
    battery = ws.get("device", {}).get("battery_pct")

    lines = ["☀️ *Morning briefing — JARVIS*", ""]
    if weather:
        lines.append(f"Weather: {weather}" + (f" at {round(temp)}°C" if temp else ""))
    if battery is not None:
        lines.append(f"Battery: {round(battery)}%")
    lines += [
        "",
        "Priorities today:",
        "1. EA submission — check status",
        "2. IELTS booking — if not booked, do it today",
        "3. UpJobs — any pending tasks?",
        "",
        "Message me to start your day.",
    ]
    await send_telegram("\n".join(lines))


async def evening_nudge():
    await send_telegram(
        "🌙 *Evening check-in — JARVIS*\n\n"
        "What did you accomplish today?\n"
        "What is the #1 priority for tomorrow?\n\n"
        "Reply here or open the JARVIS app."
    )


def start_scheduler():
    scheduler.add_job(
        morning_briefing,
        CronTrigger(hour=6, minute=30, timezone=LAGOS_TZ),
        id="morning_briefing",
        replace_existing=True,
    )
    scheduler.add_job(
        evening_nudge,
        CronTrigger(hour=21, minute=0, timezone=LAGOS_TZ),
        id="evening_nudge",
        replace_existing=True,
    )
    scheduler.start()
```

---

### 3.5 Wire Scheduler into FastAPI Startup

In `backend/main.py`, add at the bottom of the file, inside app startup:

```python
from backend.scheduler import start_scheduler

@app.on_event("startup")
async def startup_event():
    start_scheduler()
```

---

### 3.6 Wire Nudges to Telegram

When a HIGH priority nudge fires, also ping Telegram. In `backend/routers/context.py`, after the nudge is stored in Redis, add:

```python
from backend.telegram_notify import send_telegram

# Inside the receive_context function, after storing nudges:
for n in normalized_nudges:
    if n.get("priority") == "high":
        await send_telegram(f"🔴 *JARVIS Alert*\n\n{n.get('message', '')}")
```

---

### 3.7 Deploy the Telegram Update

```powershell
# Local machine
git add backend/telegram_notify.py backend/scheduler.py backend/main.py backend/routers/context.py backend/requirements.txt
git commit -m "Add Telegram notifications and APScheduler briefings"
git push origin main
```

```bash
# On Hetzner VPS
cd /var/www/jarvis
git pull origin main
docker compose -p jarvis -f docker-compose.prod.yml up -d --build
```

**Test it immediately:**

```bash
# Inside the running backend container
docker exec -it jarvis-backend-1 python -c "
import asyncio
from backend.telegram_notify import send_telegram
asyncio.run(send_telegram('JARVIS is online. Test message.'))
"
```

You should receive a Telegram message within 3 seconds.

---

## Phase 1 — Self-Learning Memory

JARVIS notices a knowledge gap, asks you a question, and saves your answer to the RAG knowledge base — permanently improving itself.

### 1.1 Create the Knowledge Update Tool

Create `backend/tools/knowledge_tools.py`:

```python
from __future__ import annotations
import asyncio
import os
from pathlib import Path
from langchain_core.tools import tool


@tool
def update_knowledge(file_slug: str, section_heading: str, content: str) -> str:
    """
    Append new knowledge to a RAG knowledge file.
    file_slug: clifford_profile | migration_plan | products | income_strategy
    section_heading: heading for the new section (e.g. 'New Skill: Rust')
    content: the knowledge content to save
    Use this when Clifford tells you something new about himself.
    """
    rag_dir = Path(__file__).resolve().parents[2] / "rag"
    allowed = {"clifford_profile", "migration_plan", "products", "income_strategy"}
    if file_slug not in allowed:
        return f"Unknown file slug '{file_slug}'. Use one of: {', '.join(allowed)}"

    target = rag_dir / f"{file_slug}.md"
    if not target.exists():
        return f"File not found: rag/{file_slug}.md"

    addition = f"\n\n## {section_heading}\n{content.strip()}\n"
    with open(target, "a", encoding="utf-8") as f:
        f.write(addition)

    return f"Saved to rag/{file_slug}.md under '{section_heading}'. Re-run rag_ingest to embed."
```

### 1.2 Add Tool to Agent

In `backend/agent.py`, import and add the tool:

```python
from backend.tools.knowledge_tools import update_knowledge

# In build_agent():
tools = [update_world_state, send_nudge, manage_goals, get_goals, web_search, update_knowledge]
```

### 1.3 Update Agent System Prompt

In `backend/agent.py`, add to the EDGE RULES section:

```
8. SELF-LEARN. When Clifford tells you something new (a skill, a financial update,
   a product milestone, a visa status change), call update_knowledge to save it.
   After saving, remind Clifford to run rag_ingest so it's embedded.
   Ask one targeted question per session to fill knowledge gaps.
```

### 1.4 Re-ingest After Learning

After JARVIS calls `update_knowledge`, run from repo root:

```powershell
$env:RAG_CHUNK_TARGET_CHARS="600"
python -m backend.scripts.rag_ingest
```

This is a manual step for now. Phase 5 will automate it via an API endpoint.

---

## Phase 2 — Google Calendar

### 2.1 Google Cloud Setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project: "JARVIS"
3. Search for "Google Calendar API" → Enable it
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Application type: **Desktop app**
6. Name: "JARVIS Calendar"
7. Download the credentials JSON file → save as `backend/google_credentials.json`

> Add `backend/google_credentials.json` to `.gitignore` — it's a secret.

### 2.2 One-Time Authorization (Run Locally)

Install dependencies:

```powershell
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Run the authorization script once:

```powershell
python -m backend.scripts.google_auth
```

This script (you'll create it below) opens a browser, asks you to allow calendar access, and saves a `token.json` file with a refresh token.

Create `backend/scripts/google_auth.py`:

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
import json

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = Path(__file__).resolve().parents[2] / "backend" / "google_credentials.json"
TOKEN_FILE = Path(__file__).resolve().parents[2] / "backend" / "google_token.json"

def main():
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json())
    creds_data = json.loads(creds.to_json())
    print("\nSuccess. Add these to your .env:")
    print(f"GOOGLE_REFRESH_TOKEN={creds_data['refresh_token']}")
    print(f"GOOGLE_CLIENT_ID={creds_data['client_id']}")
    print(f"GOOGLE_CLIENT_SECRET={creds_data['client_secret']}")

if __name__ == "__main__":
    main()
```

Copy the printed values into `.env` (local and Hetzner).

### 2.3 Create Calendar Tools

Create `backend/tools/calendar_tools.py`:

```python
from __future__ import annotations
import os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_core.tools import tool


def _get_service():
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("calendar", "v3", credentials=creds)


@tool
def get_upcoming_events(days: int = 7) -> list[dict]:
    """Retrieve Clifford's upcoming calendar events for the next N days."""
    service = _get_service()
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
    result = service.events().list(
        calendarId="primary",
        timeMin=now,
        timeMax=end,
        maxResults=20,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    events = result.get("items", [])
    return [
        {
            "summary": e.get("summary", "Untitled"),
            "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
            "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
            "description": e.get("description", ""),
            "location": e.get("location", ""),
        }
        for e in events
    ]


@tool
def create_calendar_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    location: str = "",
) -> dict:
    """
    Create a calendar event.
    start_datetime and end_datetime: ISO 8601 with timezone, e.g. '2026-05-16T09:00:00+01:00'
    """
    service = _get_service()
    event = {
        "summary": title,
        "location": location,
        "description": description,
        "start": {"dateTime": start_datetime, "timeZone": "Africa/Lagos"},
        "end": {"dateTime": end_datetime, "timeZone": "Africa/Lagos"},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return {"id": created["id"], "htmlLink": created.get("htmlLink", "")}
```

### 2.4 Add Calendar Tools to Agent

In `backend/agent.py`:

```python
from backend.tools.calendar_tools import get_upcoming_events, create_calendar_event

tools = [
    update_world_state, send_nudge, manage_goals, get_goals, web_search,
    update_knowledge, get_upcoming_events, create_calendar_event
]
```

Add to requirements.txt:
```
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
```

### 2.5 Add Calendar Context to System Prompt

In `backend/agent.py`, add to PROACTIVE MODE:

```
CALENDAR RULES:
- On every session start, call get_upcoming_events to check for today's events.
- If an event is within 2 hours → send meeting prep nudge (what is this meeting about, who is attending, what does Clifford need to know/prepare)
- If an event is tomorrow morning → send tonight reminder
- For work events at Wema Bank → connect to current priorities (migration evidence, AI projects)
```

---

## Environment Variables — Complete Reference

All variables go in `.env` at the repo root (local) and `/var/www/jarvis/.env` (Hetzner).

| Variable | Required | What it controls |
|---|---|---|
| `OPENAI_API_KEY` | Yes | LLM completions (gpt-4o-mini) + RAG embeddings (text-embedding-3-small) |
| `SUPABASE_URL` | Yes | RAG storage — https://xxxx.supabase.co |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase auth (service role, not anon) |
| `RAG_ENABLED` | Yes | `true` to enable RAG context injection |
| `RAG_SIMILARITY_THRESHOLD` | No | Default `0.2` — lower = more results |
| `RAG_CHUNK_TARGET_CHARS` | No | Default `600` — for rag_ingest script |
| `REDIS_URL` | Yes | Redis connection (overridden by docker-compose in prod) |
| `DATABASE_URL` | No | Postgres for goals (overridden by docker-compose in prod) |
| `TELEGRAM_BOT_TOKEN` | Phase 3 | Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Phase 3 | Your personal Telegram chat ID |
| `DEFAULT_TIMEZONE` | No | Default `Africa/Lagos` |
| `GOOGLE_CLIENT_ID` | Phase 2 | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Phase 2 | Google OAuth client secret |
| `GOOGLE_REFRESH_TOKEN` | Phase 2 | Long-lived token (obtained via google_auth.py) |
| `COPILOTKIT_API_KEY` | No | CopilotKit cloud (optional) |

---

## Troubleshooting

**Backend container keeps restarting:**
```bash
docker compose -p jarvis -f docker-compose.prod.yml logs backend --tail=50
```
Most common cause: missing env var (GROQ_API_KEY, SUPABASE_URL, etc.)

**Frontend on Vercel can't reach backend:**
- Check `NEXT_PUBLIC_JARVIS_URL` is set in Vercel env vars (not `.env.local`)
- Verify it is `https://` not `http://`
- Confirm Caddy is running: `systemctl status caddy`
- Confirm backend is healthy: `curl https://jarvis.yourdomain.com/health`

**RAG not returning results:**
```bash
# Confirm RAG_ENABLED=true
docker exec -it jarvis-backend-1 env | grep RAG

# Run eval from inside container
docker exec -it jarvis-backend-1 python -m backend.scripts.rag_eval
```

**Postgres migration errors on first start:**
```bash
docker compose -p jarvis -f docker-compose.prod.yml logs postgres --tail=30
# If migration files cause errors, wipe and restart:
docker compose -p jarvis -f docker-compose.prod.yml down -v
docker compose -p jarvis -f docker-compose.prod.yml up -d --build
```

**World state shows no location:**
Check if sensors.ts is sending GPS. In browser DevTools (F12 → Network), look for `POST /context` requests and inspect the body. Should include `lat` and `lng`.

**Caddy not issuing TLS certificate:**
```bash
journalctl -u caddy -n 50
```
Common cause: DNS not propagated yet. Wait 5 minutes and retry.

**Telegram messages not arriving:**
```bash
# Test the token directly
curl "https://api.telegram.org/botYOUR_TOKEN/getMe"
# Should return bot info

# Confirm chat_id is correct
curl "https://api.telegram.org/botYOUR_TOKEN/getUpdates"
# Look for "chat":{"id":...}
```
