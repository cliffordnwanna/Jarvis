# Deploy JARVIS v3 to Fly.io - Complete Guide

**FREE 3GB RAM | Fast & Reliable | No credit card for free tier**

Fly.io is a better alternative to Hugging Face Spaces if you're experiencing performance issues.

## Why Fly.io?

- ✅ **Fast** — Better performance than HF Spaces
- ✅ **FREE tier** — 3GB RAM, 160GB disk (shared-cpu-1x)
- ✅ **No credit card** required for free tier
- ✅ **Private by default** — Not public like HF Spaces
- ✅ **Persistent storage** — Data survives restarts
- ⚠️ **Sleeps after inactivity** on free tier (wakes in ~5 seconds)

## Pre-Flight Checklist ✅

- [ ] OpenAI API key ready
- [ ] Fly.io account ([fly.io](https://fly.io) - free signup)
- [ ] `flyctl` CLI installed on your computer

---

## Quick Deploy (15 minutes)

### 1. Install Fly.io CLI (3 min)

**Windows (PowerShell):**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

**Verify installation:**
```powershell
flyctl version
```

### 2. Sign Up & Login (2 min)

```powershell
flyctl auth signup
```

Or if you already have an account:
```powershell
flyctl auth login
```

### 3. Create fly.toml Configuration (2 min)

Create `fly.toml` in your Jarvis repo root:

```toml
app = "jarvis-ai-YOUR_NAME"  # Change this to be unique
primary_region = "iad"  # US East (change to your nearest region)

[build]
  dockerfile = "Dockerfile.flyio"

[env]
  PORT = "8080"
  HOST = "0.0.0.0"
  ENABLE_SIGNUP = "true"
  DEFAULT_MODELS = "gpt-4o,gpt-4o-mini"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"  # Free tier: stop after inactivity
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  memory = "2gb"
  cpu_kind = "shared"
  cpus = 1

[mounts]
  source = "jarvis_data"
  destination = "/app/backend/data"
  initial_size = "1gb"
```

### 4. Create Dockerfile for Fly.io (2 min)

Create `Dockerfile.flyio` in your repo:

```dockerfile
FROM ghcr.io/open-webui/open-webui:main

# Fly.io configuration
ENV PORT=8080
ENV HOST=0.0.0.0

# These will be set via fly secrets
ENV WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# Use OpenAI directly
ENV OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL:-https://api.openai.com/v1}

# Enable signup for first user (becomes admin)
ENV ENABLE_SIGNUP=true

# Default models
ENV DEFAULT_MODELS=gpt-4o,gpt-4o-mini

# Data persistence
VOLUME /app/backend/data

EXPOSE 8080

CMD ["bash", "start.sh"]
```

### 5. Launch Your App (3 min)

```powershell
# Navigate to your Jarvis repo
cd c:\Jarvis

# Launch (this creates the app and deploys)
flyctl launch --no-deploy
```

**Answer the prompts:**
- **App name:** `jarvis-ai-yourname` (must be globally unique)
- **Region:** Choose closest to you (e.g., `iad` for US East)
- **PostgreSQL database?** No
- **Redis database?** No
- **Deploy now?** No (we'll add secrets first)

### 6. Create Persistent Volume (1 min)

```powershell
flyctl volumes create jarvis_data --region iad --size 1
```

Change `iad` to your chosen region.

### 7. Add Secrets (2 min)

```powershell
# Add OpenAI API key
flyctl secrets set OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE

# Generate and add secret key (run this to generate random string)
$secret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
flyctl secrets set WEBUI_SECRET_KEY=$secret
```

### 8. Deploy! (2 min)

```powershell
flyctl deploy
```

Wait 2-3 minutes for build and deployment.

### 9. Open Your JARVIS

```powershell
flyctl open
```

Your app URL: `https://jarvis-ai-yourname.fly.dev`

---

## Complete Setup (10 minutes)

### 10. Create Admin Account (1 min)

1. Your app opens in browser
2. Click **Sign Up**
3. Enter name, email, password
4. Click **Create Account**
5. You're now admin!

### 11. Enable Features (5 min)

#### Enable Web Search

1. **Admin Panel** → **Settings** → **Web Search**
2. **Enable Web Search:** Toggle ON
3. **Search Engine:** Select **DDGS** (DuckDuckGo)
4. Click **Save**

#### Enable Memories

1. **Settings** → **Features**
2. Find **Memories (Beta)**
3. Toggle ON
4. Click **Save**

#### Enable Audio (Voice Features)

1. **Settings** → **Audio**
2. **Speech-to-Text:**
   - Engine: OpenAI
   - Model: whisper-1
3. **Text-to-Speech:**
   - Engine: OpenAI
   - Model: tts-1
   - Voice: nova (or your preference)
4. Click **Save**

### 12. Upload v3 Pipeline (4 min)

1. **Settings** → **Pipelines**
2. Click **+ Add Pipeline**
3. Open `c:\Jarvis\pipelines\merge_thinking_orchestrator.py`
4. Copy ALL contents (Ctrl+A, Ctrl+C)
5. Paste into pipeline editor
6. Click **Save**
7. Enable pipeline (toggle ON)
8. Configure valves:
   ```
   monthly_budget_usd: 50
   max_context_tokens: 8000
   enable_orchestrator: true
   enable_cost_tracking: true
   enable_pattern_learning: true
   ask_user_first: true
   ```
9. Click **Save**

---

## Test End-to-End (5 minutes)

### Test 1: Basic Chat
1. New chat → Select `gpt-4o`
2. Send: "Hello! What can you help me with?"
3. ✅ Should get response

### Test 2: Merge Thinking
1. New chat
2. Send: "How should I launch upjobs.co?"
3. ✅ Expected: "How would YOU handle this?"
4. Answer: "I'd use Product Hunt, Twitter, LinkedIn"
5. ✅ JARVIS should research and merge perspectives

### Test 3: Web Search
1. New chat
2. Send: "What are the latest AI trends in 2026?"
3. ✅ Should see web search tool being used
4. ✅ Should get current information

### Test 4: Voice (Mobile)
1. Open app on phone: `https://jarvis-ai-yourname.fly.dev`
2. Tap 🎤 microphone icon
3. Speak: "How should I price my SaaS?"
4. ✅ Should transcribe and respond

---

## Manage Your Deployment

### View Logs
```powershell
flyctl logs
```

### Check Status
```powershell
flyctl status
```

### Scale Resources (if needed)
```powershell
# Increase memory to 4GB (costs ~$5/month)
flyctl scale memory 4096

# Keep always running (costs ~$5/month)
flyctl scale count 1
```

### SSH into Your App
```powershell
flyctl ssh console
```

### Update Deployment
```powershell
# After making changes to Dockerfile or code
flyctl deploy
```

### View Secrets
```powershell
flyctl secrets list
```

### Add More Secrets
```powershell
flyctl secrets set ANTHROPIC_API_KEY=sk-ant-...
```

---

## Troubleshooting

### App Not Starting

**Check logs:**
```powershell
flyctl logs
```

**Common issues:**
- Missing secrets (OPENAI_API_KEY, WEBUI_SECRET_KEY)
- Volume not mounted
- Port mismatch

**Fix:**
```powershell
# Verify secrets exist
flyctl secrets list

# Verify volume exists
flyctl volumes list

# Restart app
flyctl apps restart jarvis-ai-yourname
```

### App Sleeping on Free Tier

**Symptom:** First request takes 5-10 seconds

**This is normal on free tier.** App sleeps after inactivity.

**Solutions:**
- Accept the cold start (fine for personal use)
- Keep always running: `flyctl scale count 1` (~$5/month)

### Out of Memory

**Symptom:** App crashes, logs show OOM errors

**Solutions:**
```powershell
# Increase to 4GB RAM (~$5/month)
flyctl scale memory 4096
```

### Volume Full

**Check volume usage:**
```powershell
flyctl ssh console
df -h
```

**Increase volume size:**
```powershell
flyctl volumes extend <volume-id> --size 2
```

### Can't Access from Mobile

**Ensure HTTPS is working:**
1. Check `fly.toml` has `force_https = true`
2. Redeploy: `flyctl deploy`
3. Access via `https://` not `http://`

---

## Cost Breakdown

### Free Tier (What You Get)
- ✅ 3GB RAM shared-cpu-1x
- ✅ 160GB outbound data transfer
- ✅ 1GB persistent volume
- ✅ Auto-stop/start (sleeps when idle)
- **Cost:** $0/month

### Paid Options (If You Need More)

**Always Running (No Sleep):**
- `flyctl scale count 1`
- **Cost:** ~$5/month

**More RAM (4GB):**
- `flyctl scale memory 4096`
- **Cost:** ~$5/month

**Larger Volume (10GB):**
- `flyctl volumes extend <id> --size 10`
- **Cost:** ~$1/month

**Total for production-ready setup:** ~$10/month

---

## Mobile Access Setup

### Add to Phone Home Screen

**iPhone (Safari):**
1. Open `https://jarvis-ai-yourname.fly.dev`
2. Tap Share → Add to Home Screen
3. Name it "JARVIS"
4. Tap Add

**Android (Chrome):**
1. Open `https://jarvis-ai-yourname.fly.dev`
2. Menu → Add to Home Screen
3. Name it "JARVIS"
4. Tap Add

### Use with AirPods

1. Connect AirPods to phone
2. Open JARVIS app
3. Tap 🎤 to speak
4. Enable auto-play in Settings → Audio
5. Responses play through AirPods automatically

---

## Advantages Over Hugging Face Spaces

| Feature | Fly.io | HF Spaces |
|---------|--------|-----------|
| **Performance** | ⚡ Fast | 🐌 Slow/hangs |
| **RAM** | 3GB | 16GB |
| **Storage** | 160GB | 50GB |
| **Privacy** | ✅ Private | ❌ Public |
| **Wake time** | ~5 seconds | ~30-60 seconds |
| **Reliability** | ✅ Stable | ⚠️ Unstable |
| **Cost** | Free → $5-10 | Free forever |

**Fly.io is better if:**
- HF Spaces is hanging/slow
- You need private deployment
- You want faster wake times
- You need reliability

**HF Spaces is better if:**
- You need more RAM (16GB)
- You want 100% free forever
- You don't mind public deployment

---

## Next Steps

### Optimize Performance

1. **Enable caching:**
   - Settings → Models → Enable model caching
   
2. **Reduce context:**
   - Pipeline valves → `max_context_tokens: 4000`

3. **Use faster models:**
   - `gpt-4o-mini` for most tasks
   - `gpt-4o` only for complex merges

### Add More Features

1. **Knowledge bases:**
   - Upload your documents
   - Enable RAG for context-aware responses

2. **Custom prompts:**
   - Create reusable prompts
   - Version control with Git

3. **Channels:**
   - Team collaboration
   - Shared conversations

### Monitor Costs

**Check Fly.io usage:**
```powershell
flyctl dashboard
```

**Check OpenAI usage:**
- Admin Panel → Analytics
- Track token consumption
- Validate 85% savings claim

---

## Deployment Complete! 🎉

You now have:
- ✅ JARVIS running on Fly.io (fast & reliable)
- ✅ v3 Orchestrator with merge thinking
- ✅ Web search enabled
- ✅ Voice features (AirPods support)
- ✅ Mobile access
- ✅ Private deployment
- ✅ Persistent storage

**Your JARVIS URL:** `https://jarvis-ai-yourname.fly.dev`

**Access from anywhere:**
- Desktop: Open URL in browser
- Mobile: Add to home screen
- Voice: Use AirPods with 🎤 button

Start chatting and test merge thinking!
