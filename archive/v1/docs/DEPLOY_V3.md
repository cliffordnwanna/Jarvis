# Deploy JARVIS v3 Orchestrator to Railway - Complete Guide

## Pre-Flight Checklist ✅

- [ ] `.env` file created with at least `OPENAI_API_KEY` (copy from `.env.example`)
- [ ] Code committed to GitHub (your repo must be public or Railway connected)
- [ ] Railway account ready ([railway.app](https://railway.app) - free tier available)
- [ ] OpenAI API key ready (get from [platform.openai.com/api-keys](https://platform.openai.com/api-keys))

## Step-by-Step (15 minutes)

### 1. Push to GitHub (2 min)

```bash
git add -A
git commit -m "JARVIS v3 orchestrator ready for deployment"
git push origin main
```

### 2. Create Railway Project (1 min)

1. Go to [railway.app](https://railway.app)
2. **+ New Project** → **Empty Project**
3. Name it: `jarvis-personal-ai`

### 3. Deploy LiteLLM Service (5 min)

**Railway doesn't support docker-compose.yml multi-service deploys.** You need to create **two separate services** in one project.

#### 3.1 Create LiteLLM Service

1. In your Railway project → **+ New** → **GitHub Repo**
2. Select your `Jarvis` repository
3. **Service Settings:**
   - Click the service → **Settings** tab
   - **Service Name:** `litellm`
   - **Root Directory:** `/` (leave default)
   - **Build:**
     - **Builder:** Docker
     - **Dockerfile Path:** `Dockerfile.litellm`
   - **Deploy:**
     - **Start Command:** (leave empty, Dockerfile handles it)

4. **Add Environment Variables:**
   - Click **Variables** tab → **+ New Variable**
   - Add these one by one:
     ```
     OPENAI_API_KEY=sk-proj-...
     PORT=4000
     ```
   - **Optional (add later):**
     ```
     ANTHROPIC_API_KEY=sk-ant-...
     OPENROUTER_API_KEY=sk-or-...
     ```

5. **Note the Internal Hostname:**
   - Click **Networking** tab
   - You'll see something like: `litellm.railway.internal`
   - **Copy this** — you'll need it for Open WebUI

6. **Deploy:**
   - Click **Deploy** (top right)
   - Wait 3-4 minutes
   - Check **Deployments** tab — should show "Success ✓"
   - Check **Logs** — should see: `Uvicorn running on http://0.0.0.0:4000`

#### 3.2 Verify LiteLLM is Working

- In **Logs**, look for:
  ```
  INFO:     Started server process
  INFO:     Uvicorn running on http://0.0.0.0:4000
  ```
- If you see errors about API keys, double-check your `OPENAI_API_KEY` variable

### 4. Deploy Open WebUI Service (5 min)

#### 4.1 Create Open WebUI Service

1. In the **same Railway project** → **+ New** → **GitHub Repo**
2. Select your `Jarvis` repository again
3. **Service Settings:**
   - **Service Name:** `open-webui`
   - **Root Directory:** `/`
   - **Build:**
     - **Builder:** Docker
     - **Dockerfile Path:** `Dockerfile.openwebui`

4. **Add Environment Variables:**
   - Click **Variables** tab → **+ New Variable**
   - **CRITICAL:** Replace `litellm.railway.internal` with YOUR actual LiteLLM hostname from step 3.1.5
   
   ```
   OPENAI_API_BASE_URL=http://litellm.railway.internal:4000/v1
   OPENAI_API_KEY=sk-jarvis-railway
   WEBUI_SECRET_KEY=BAvR0YxlVoZus4iHwFKeUICq7z2MjLm
   ENABLE_SIGNUP=true
   DEFAULT_MODELS=jarvis-gpt
   PORT=8080
   RAG_EMBEDDING_ENGINE=
   ```
   
   **Note:** `RAG_EMBEDDING_ENGINE=` (empty) disables ChromaDB to save disk space. You can enable RAG later by removing this variable.
   
   **Generate your own WEBUI_SECRET_KEY:**
   - Go to [random.org/strings](https://www.random.org/strings/?num=1&len=32&digits=on&upperalpha=on&loweralpha=on&unique=on&format=plain)
   - Copy the random string
   - Replace the example above

5. **Generate Public Domain:**
   - Click **Networking** tab
   - Click **Generate Domain**
   - You'll get a URL like: `https://open-webui-production-xxxx.up.railway.app`
   - **Bookmark this** — this is your JARVIS URL

6. **Configure Volume (CRITICAL):**
   - Click **Data** tab
   - You'll see a volume created automatically
   - **Click the volume** → **Settings**
   - **Size:** Change from 500MB to **5GB** (or more if you plan to upload many documents)
   - Click **Save**
   
   **Why:** ChromaDB (vector database) needs ~2GB minimum. Railway's default 500MB causes "disk full" crashes.

7. **Deploy:**
   - Click **Deploy**
   - Wait 3-4 minutes
   - Check **Logs** — should see: `Application startup complete`

#### 4.2 Verify Open WebUI is Working

- Open your public URL in browser
- You should see the Open WebUI login/signup page
- If you get 502 errors, wait 2 more minutes (services still starting)

### 5. Initial Setup in Open WebUI (3 min)

#### 5.1 Create Admin Account

1. Open your Railway public URL
2. Click **Sign Up**
3. Enter:
   - **Name:** Your name
   - **Email:** Your email
   - **Password:** Strong password
4. Click **Create Account**
5. You're now logged in as admin

#### 5.2 Verify Models are Available

1. Look at the top of the chat interface
2. Click the **model selector dropdown**
3. You should see:
   - `jarvis-gpt` (OpenAI GPT-4o)
   - `jarvis-gpt-mini` (OpenAI GPT-4o-mini)
   - If you added other API keys: `jarvis-claude`, `jarvis-router-*`, etc.

**If no models appear:**
- Check LiteLLM service logs for API key errors
- Verify `OPENAI_API_BASE_URL` points to correct internal hostname
- Restart Open WebUI service

### 6. Upload v3 Orchestrator Pipeline (3 min)

#### 6.1 Add the Pipeline

1. Click your **profile icon** (top right) → **Admin Panel**
2. Go to **Settings** → **Pipelines**
3. Click **+ Add Pipeline** (or **+** button)
4. **Copy the pipeline code:**
   - Open `pipelines/merge_thinking_orchestrator.py` in your IDE
   - Select ALL (Ctrl+A / Cmd+A)
   - Copy (Ctrl+C / Cmd+C)
5. **Paste into Pipeline editor:**
   - Paste the code (Ctrl+V / Cmd+V)
   - Click **Save** (bottom right)
6. **Enable the pipeline:**
   - Find "JARVIS Merge Orchestrator v3" in the list
   - Toggle the switch to **ON** (should turn blue/green)

#### 6.2 Configure Pipeline Settings (Valves)

1. Click the **⚙️ settings icon** next to the pipeline
2. You'll see configuration options (Valves)
3. **Recommended settings:**
   ```
   monthly_budget_usd: 50
   max_context_tokens: 8000
   enable_orchestrator: true
   enable_cost_tracking: true
   enable_pattern_learning: true
   ask_user_first: true
   ```
4. Click **Save**

### 7. Test Merge Thinking (2 min)

#### 7.1 First Merge Test

1. Go back to the **chat interface** (click "New Chat" if needed)
2. **Select model:** Click dropdown → Choose `jarvis-gpt`
3. **Send test question:**
   ```
   How should I price my SaaS product?
   ```
4. **Expected response:**
   ```
   How would YOU handle this?
   ```
   ✅ If you see this, merge thinking is working!

5. **Answer with your approach:**
   ```
   I'd charge $99/month based on what competitors are charging
   ```

6. **JARVIS will now:**
   - Research independently (may use web search if enabled)
   - Compare your approach with its analysis
   - Show where you align and disagree
   - Give final recommendation

#### 7.2 Verify Cost Tracking

After your first merge:

1. Go to Railway → `open-webui` service → **Data** tab
2. You should see a volume mounted at `/app/backend/data`
3. Files created:
   - `jarvis_merge_state.json` — Current merge sessions
   - `jarvis_merge_history.json` — Past 50 merges
   - `jarvis_cost_tracking.json` — Cost per session + monthly total

**To download and check:**
- Railway doesn't have direct file browser
- Use Railway CLI or check logs for cost summaries
- Orchestrator will show budget warnings in responses when you hit 80%

### 8. Complete Open WebUI Setup (5 min)

---

## What You Get with v3

✅ **85% cost savings** vs v1 (3,000 tokens vs 15,000 per merge)  
✅ **Budget management** — Alerts at 80%, switches to brief mode at 100%  
✅ **Pattern learning** — Remembers your past decisions  
✅ **Multi-turn merge** — Iterate with "What if I changed X?"  
✅ **No token limit errors** — Intelligent compression prevents failures  

---

#### 8.1 Add Your Custom System Prompt

1. Click **model selector** → Click **⚙️** next to `jarvis-gpt`
2. Scroll to **System Prompt** field
3. **Open `docs/system_prompt.md` in your IDE**
4. **Customize the User Context section:**
   ```markdown
   **Name:** [Your actual name]
   **Background:** [Your profession, e.g., "Software engineer and entrepreneur"]
   **Goals:** [Your current priorities, e.g., "Launch SaaS product, grow to $10k MRR"]
   **Working style:** [e.g., "Direct feedback, no sugarcoating"]
   **Pet peeves:** [e.g., "Vague advice, analysis paralysis"]
   ```
5. **Copy the entire customized prompt**
6. **Paste into System Prompt field**
7. Click **Save**

#### 8.2 Enable Web Search (Critical for Merge Thinking)

1. **Admin Panel** → **Settings** → **Web Search**
2. **Enable:** Toggle ON
3. **Search Engine:** Select **DuckDuckGo** (free, no API key needed)
4. **Advanced (optional):**
   - For better results, use **SearXNG** (requires self-hosting)
   - Or **Brave Search** (requires API key from brave.com/search/api)
5. Click **Save**

**Why this matters:** Merge thinking tells the LLM to "research independently" — web search enables this.

#### 8.3 Enable Memory (Persistent Context)

1. Click your **profile icon** → **Settings**
2. Go to **Personalization** → **Memory**
3. Toggle **Enable Memory** to ON
4. **Memory Settings:**
   - **Auto-save:** ON (JARVIS remembers facts automatically)
   - **Memory Scope:** Personal (only you see your memories)
5. Click **Save**

**Test memory:**
- Tell JARVIS: "Remember that I'm building a SaaS product for small businesses"
- In a new chat, ask: "What am I working on?"
- JARVIS should recall your SaaS project

#### 8.4 Enable Voice Input/Output (Optional)

1. **Settings** → **Audio**
2. **Speech-to-Text:**
   - **Engine:** Browser (free, works offline)
   - Or **OpenAI Whisper** (requires API key, more accurate)
3. **Text-to-Speech:**
   - **Engine:** Browser (free)
   - Or **OpenAI TTS** (requires API key, better quality)
4. Click **Save**

**Test voice:**
- Click the 🎤 microphone icon in chat
- Speak your question
- JARVIS will transcribe and respond

---

## Monitoring

### Check Costs
- View `jarvis_cost_tracking.json` in Open WebUI data volume
- Shows per-session costs and monthly total

### Check Merge History
- View `jarvis_merge_history.json` in data volume
- Shows last 50 merge sessions with patterns

### Adjust Budget
- Pipeline settings → `monthly_budget_usd` → Change value
- Default: $50/month

---

## Troubleshooting Common Issues

### Models Not Appearing

**Symptom:** Model dropdown is empty or shows "No models available"

**Solutions:**
1. **Check LiteLLM logs:**
   - Railway → `litellm` service → **Deployments** → Click latest → **View Logs**
   - Look for errors like: `AuthenticationError: Invalid API key`
2. **Verify environment variables:**
   - `litellm` service → **Variables** tab
   - Ensure `OPENAI_API_KEY` starts with `sk-proj-` or `sk-`
   - Check for typos or extra spaces
3. **Check Open WebUI connection:**
   - `open-webui` service → **Variables**
   - Verify `OPENAI_API_BASE_URL=http://litellm.railway.internal:4000/v1`
   - Make sure it ends with `/v1`
4. **Restart services:**
   - Click **Redeploy** on both services
   - Wait 3-4 minutes

### Pipeline Not Working

**Symptom:** Asking "How should I..." doesn't trigger "How would YOU handle this?"

**Solutions:**
1. **Check pipeline is enabled:**
   - Admin Panel → Pipelines
   - Toggle should be ON (blue/green)
2. **Check for syntax errors:**
   - Click pipeline → **Edit**
   - Look for red error indicators
   - Common issue: Missing quotes or indentation
3. **Verify trigger words:**
   - Pipeline settings → `merge_trigger_words`
   - Should include: `how should,best way,decide,decision`
4. **Check `ask_user_first` setting:**
   - Pipeline settings → `ask_user_first: true`
5. **Test with exact phrase:**
   - Try: "How should I price my product?" (known trigger)

### 502 Bad Gateway Errors

**Symptom:** Can't access Open WebUI URL, shows 502 error

**Solutions:**
1. **Wait longer:** Services take 3-6 minutes to fully start
2. **Check deployment status:**
   - Railway → `open-webui` service → **Deployments**
   - Should show "Success ✓" not "Building..." or "Failed"
3. **Check logs for crashes:**
   - **View Logs** → Look for errors
   - Common: `Port 8080 already in use` (shouldn't happen on Railway)
4. **Verify PORT variable:**
   - `open-webui` service → **Variables**
   - Should have `PORT=8080`
5. **Redeploy:**
   - Click **Redeploy** → Wait 4-5 minutes

### LiteLLM Connection Errors

**Symptom:** Open WebUI loads but shows "Failed to connect to LiteLLM"

**Solutions:**
1. **Check internal hostname:**
   - `litellm` service → **Networking** tab
   - Copy the internal hostname (e.g., `litellm.railway.internal`)
2. **Update Open WebUI variable:**
   - `open-webui` service → **Variables**
   - `OPENAI_API_BASE_URL=http://[YOUR_LITELLM_HOSTNAME]:4000/v1`
   - Replace `[YOUR_LITELLM_HOSTNAME]` with actual hostname
3. **Verify LiteLLM is running:**
   - `litellm` service → **Logs**
   - Should see: `Uvicorn running on http://0.0.0.0:4000`
4. **Check both services are in same project:**
   - Railway internal networking only works within same project

### Cost Tracking Not Working

**Symptom:** No cost data in files, no budget warnings

**Solutions:**
1. **Check valve settings:**
   - Pipeline settings → `enable_cost_tracking: true`
2. **Verify file permissions:**
   - Open WebUI needs write access to `/app/backend/data`
   - Railway volumes should handle this automatically
3. **Check for errors in logs:**
   - `open-webui` service → **Logs**
   - Search for: `jarvis_cost_tracking`
4. **Manual test:**
   - Do 2-3 merges
   - Check if `monthly_budget_usd` warnings appear in responses

### Memory Not Persisting

**Symptom:** JARVIS forgets things between sessions

**Solutions:**
1. **Verify memory is enabled:**
   - Settings → Personalization → Memory → ON
2. **Check volume is mounted:**
   - Railway → `open-webui` service → **Data** tab
   - Should show volume at `/app/backend/data`
3. **Test memory manually:**
   - Tell JARVIS: "Remember my name is [Your Name]"
   - New chat → Ask: "What's my name?"
   - Should recall correctly
4. **Check for database errors:**
   - Logs → Search for: `database` or `sqlite`

### Database or Disk is Full Error

**Symptom:** Logs show `chromadb.errors.InternalError: database or disk is full` and service crashes

**This is the most common Railway deployment error.**

**Solutions:**
1. **Increase volume size (REQUIRED):**
   - Railway → `open-webui` service → **Data** tab
   - Click your volume (e.g., `open-webui-data`)
   - **Settings** → **Size:** Change to **5GB** minimum
   - Click **Save**
   - **Redeploy** the service

2. **Alternative - Disable RAG temporarily:**
   - If you don't need document uploads yet
   - **Variables** tab → Add:
     ```
     RAG_EMBEDDING_ENGINE=
     ```
   - This disables ChromaDB entirely (saves ~2GB)
   - Redeploy

3. **Check current disk usage:**
   - **Metrics** tab → Look at "Disk Usage"
   - Should be <80% after increasing volume

4. **Clean up old data (if needed):**
   - Railway CLI: `railway run bash`
   - `du -sh /app/backend/data/*`
   - Delete old ChromaDB data if migrating

**Why this happens:**
- Railway's default volume is 500MB
- ChromaDB needs ~2GB for vector database initialization
- Open WebUI data (chats, memory, uploads) adds more
- **Solution:** Always set volume to 5GB+ before first deploy

### Out of Memory (OOM) Errors

**Symptom:** Deployment fails with "Out of Memory (OOM)"

**Solutions:**
1. **Upgrade Railway plan:**
   - Free tier: 512MB RAM (not enough for Open WebUI)
   - Hobby plan ($5/mo): 8GB RAM (recommended)
   - Railway → Project Settings → Upgrade

2. **Reduce memory usage (temporary):**
   - Disable RAG: `RAG_EMBEDDING_ENGINE=`
   - Disable memory: Don't enable Memory feature
   - Use smaller models via LiteLLM

3. **Check memory usage:**
   - **Metrics** tab → "Memory Usage"
   - Open WebUI typically needs 1-2GB RAM
   - ChromaDB adds another 500MB-1GB

**Note:** Railway's free tier is insufficient for production Open WebUI. Upgrade to Hobby ($5/mo) for reliable deployment.

---

## Next Steps After Deployment

1. **Test 5-10 merges** to validate quality
2. **Check cost tracking** after 24 hours
3. **Customize system prompt** with your personal info
4. **Add more models** via `litellm_config.yaml` if needed
5. **Monitor monthly costs** in cost_tracking.json

---

## Cost Estimates (v3 Orchestrator)

| Usage Level | Merges/Day | Monthly Cost |
|-------------|------------|--------------|
| Light | 5 | $1.20 |
| Medium | 20 | $4.80 |
| Heavy | 50 | $12.00 |
| Very Heavy | 100 | $24.00 |

**Plus general chat:** ~$10-20/month  
**Total estimated:** $15-45/month (well within $50 budget)

---

**You're ready to deploy!** Follow steps 1-6 above and you'll have JARVIS live in 15 minutes.
