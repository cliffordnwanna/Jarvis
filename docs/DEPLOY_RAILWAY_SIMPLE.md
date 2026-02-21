# Deploy JARVIS to Railway - Simplified & Reliable

**Most reliable option for cross-platform testing**

Railway is the most stable platform for Open WebUI, despite previous issues. This guide fixes the disk space problem.

## Why Railway Now?

- ✅ **Most reliable** — Better uptime than HF Spaces or Fly.io
- ✅ **Fast** — No hanging or slowness
- ✅ **Simple** — Deploy directly from GitHub
- ✅ **Persistent** — Data survives restarts
- ✅ **$5/month** — Affordable after $5 free trial
- ✅ **Works everywhere** — Desktop, mobile, all platforms

## Pre-Flight Checklist

- [ ] GitHub repo pushed with latest code
- [ ] Railway account ([railway.app](https://railway.app))
- [ ] OpenAI API key ready
- [ ] Credit card (for $5 trial, then $5/month)

---

## Deploy (10 minutes)

### 1. Create Railway Account (2 min)

1. Go to [railway.app](https://railway.app)
2. Click **Login with GitHub**
3. Authorize Railway
4. Add payment method (gets $5 free trial)

### 2. Create New Project (1 min)

1. Click **+ New Project**
2. Select **Deploy from GitHub repo**
3. Choose your `Jarvis` repository
4. Click **Deploy Now**

### 3. Configure Service (3 min)

Railway will start building. While it builds:

1. Click your service name
2. Click **Settings** tab
3. **Root Directory:** Leave as `/`
4. **Build:**
   - **Builder:** Dockerfile
   - **Dockerfile Path:** `Dockerfile.railway`
5. **Deploy:**
   - **Start Command:** (leave empty)

### 4. Add Environment Variables (2 min)

1. Click **Variables** tab
2. Click **+ New Variable** and add these:

```
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
WEBUI_SECRET_KEY=YOUR_32_CHAR_RANDOM_STRING
PORT=8080
ENABLE_SIGNUP=true
DEFAULT_MODELS=gpt-4o,gpt-4o-mini

# CRITICAL: Disable ChromaDB to avoid disk space issues
RAG_EMBEDDING_ENGINE=
ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION=false
```

3. Click **Deploy** (triggers redeploy with new variables)

### 5. Add Volume (CRITICAL - 2 min)

**This prevents disk space errors:**

1. Click **Settings** tab
2. Scroll to **Volumes**
3. Click **+ New Volume**
4. **Mount Path:** `/app/backend/data`
5. **Size:** 5GB (minimum to avoid ChromaDB issues)
6. Click **Add**

Service will redeploy automatically.

### 6. Generate Domain (1 min)

1. Click **Settings** tab
2. Scroll to **Networking**
3. Click **Generate Domain**
4. Your URL: `https://your-service.up.railway.app`

---

## Access JARVIS (5 minutes)

### 7. Open Your App

1. Click the generated domain URL
2. Wait 30 seconds for first load
3. You'll see Open WebUI login page

### 8. Create Admin Account

1. Click **Sign Up**
2. Enter name, email, password
3. Click **Create Account**
4. You're admin!

### 9. Enable Features

#### Web Search
1. **Admin Panel** → **Settings** → **Web Search**
2. Toggle **ON**
3. Select **DDGS** (DuckDuckGo)
4. Click **Save**

#### Memories
1. **Settings** → **Features**
2. Find **Memories (Beta)**
3. Toggle **ON**
4. Click **Save**

#### Audio (Voice)
1. **Settings** → **Audio**
2. **STT Engine:** OpenAI
3. **STT Model:** whisper-1
4. **TTS Engine:** OpenAI
5. **TTS Model:** tts-1
6. **Voice:** nova
7. Click **Save**

### 10. Upload v3 Pipeline

1. **Settings** → **Pipelines**
2. Click **+ Add Pipeline**
3. Copy contents from `c:\Jarvis\pipelines\merge_thinking_orchestrator.py`
4. Paste into editor
5. Click **Save**
6. Enable pipeline (toggle ON)
7. Configure valves:
   ```
   monthly_budget_usd: 50
   max_context_tokens: 8000
   enable_orchestrator: true
   enable_cost_tracking: true
   ```
8. Click **Save**

---

## Test End-to-End (5 minutes)

### Test 1: Basic Chat
1. New chat → Select `gpt-4o`
2. Send: "Hello!"
3. ✅ Should respond

### Test 2: Merge Thinking
1. New chat
2. Send: "How should I launch upjobs.co?"
3. ✅ Expected: "How would YOU handle this?"
4. Answer with your approach
5. ✅ JARVIS researches and merges

### Test 3: Voice (Mobile)
1. Open Railway URL on phone
2. Add to home screen
3. Tap 🎤 microphone
4. Speak a question
5. ✅ Should transcribe and respond

---

## Troubleshooting

### Build Failed

**Check logs:**
1. Click **Deployments** tab
2. Click latest deployment
3. View build logs

**Common issues:**
- Missing `Dockerfile.railway`
- Syntax errors in Dockerfile

**Fix:** Create the Dockerfile (see next section)

### Disk Full Error

**Symptom:** "database or disk is full"

**Fix:**
1. Verify volume is 5GB minimum
2. Check environment variables include `RAG_EMBEDDING_ENGINE=`
3. Redeploy

### Out of Memory

**Symptom:** Service crashes, OOM in logs

**Fix:**
1. Click **Settings** → **Resources**
2. Increase memory to 2GB or 4GB
3. Costs ~$10-15/month

### Can't Access from Mobile

**Ensure HTTPS:**
1. Use the Railway-generated domain
2. Don't use custom HTTP domains
3. Railway auto-provisions SSL

---

## Cost Breakdown

### Free Trial
- $5 credit on signup
- Lasts ~1 month with basic usage

### After Trial
- **Minimum:** $5/month
- **Typical usage:** $5-10/month
  - 512MB RAM: $5
  - 1GB RAM: $7
  - 2GB RAM: $10
  - 5GB volume: Included

### OpenAI API (Separate)
- GPT-4o: ~$3-5/month with v3 orchestrator
- Whisper STT: ~$2-3/month
- TTS: ~$1-2/month
- **Total AI costs:** ~$6-10/month

**Grand total:** ~$15-20/month for full JARVIS with voice

---

## Mobile Access

### Add to Home Screen

**iPhone:**
1. Open Railway URL in Safari
2. Tap Share → Add to Home Screen
3. Name it "JARVIS"

**Android:**
1. Open Railway URL in Chrome
2. Menu → Add to Home Screen
3. Name it "JARVIS"

### Use with AirPods

1. Connect AirPods
2. Open JARVIS app
3. Tap 🎤 to speak
4. Enable auto-play in Settings → Audio
5. Responses play through AirPods

---

## Why Railway is Best for You

| Feature | Railway | HF Spaces | Fly.io |
|---------|---------|-----------|--------|
| **Reliability** | ✅ Excellent | ❌ Hangs | ❌ Failed |
| **Speed** | ✅ Fast | ❌ Slow | ✅ Fast |
| **Mobile** | ✅ Perfect | ⚠️ Works | ⚠️ Works |
| **Voice** | ✅ Perfect | ⚠️ Works | ⚠️ Works |
| **Setup** | ✅ Simple | ⚠️ Complex | ⚠️ Complex |
| **Cost** | $5-10/mo | Free | Free-$5 |
| **Support** | ✅ Good | ❌ None | ⚠️ Limited |

**Railway wins for:**
- Reliability (most important!)
- Cross-platform testing
- Production use
- Mobile access
- Voice features

**Worth the $5-10/month** for a stable, fast JARVIS you can rely on.

---

## Next Steps

1. **Create Railway account**
2. **Push code to GitHub** (if not already)
3. **Create Dockerfile.railway** (see below)
4. **Deploy from GitHub**
5. **Add environment variables**
6. **Create 5GB volume**
7. **Test everything**

Ready to create the Dockerfile and deploy!
