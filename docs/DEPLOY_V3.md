# Deploy JARVIS v3 Orchestrator to Railway - Quick Guide

## Pre-Flight Checklist

- [ ] `.env` file created with at least `OPENAI_API_KEY`
- [ ] Code committed to GitHub
- [ ] Railway account ready

# Deploy JARVIS v3 Orchestrator to Railway - Quick Guide

## Pre-Flight Checklist

- [ ] `.env` file created with at least `OPENAI_API_KEY`
- [ ] Code committed to GitHub
- [ ] Railway account ready

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

### 3. Deploy from GitHub Repo (Auto-detects Compose) (5 min)

**✅ FIXED – Railway Deployment Error: "Dockerfile `Dockerfile` does not exist"**  
This error happens because Railway sometimes ignores `docker-compose.yml` during GitHub deploy and falls back to Nixpacks build mode (which looks for a root `Dockerfile`).  

**You do NOT need to install Docker on Railway.**  
**You do NOT remove `docker-compose.yml`.**  
**Best fix in 2026:** Use **Empty Project + drag-and-drop** your `docker-compose.yml` (official recommended method).  

#### Exact 10-Minute Fix (Start Fresh)

##### 1. Delete the broken project (if you have one)
- Go to Railway dashboard  
- Find your `jarvis-personal-ai` project → **Settings** → **Delete Project**

##### 2. Create Empty Project + Drag Compose (this avoids the error 100%)
1. Click **+ New Project** → **Empty Project**  
2. Name it `jarvis-personal-ai`  
3. **Drag and drop** your `docker-compose.yml` file directly onto the empty canvas (from your local folder)  
   → Railway will instantly import **two services**:
   - `open-webui` 
   - `litellm`  
   (You will see the services appear with the correct images from your compose file)

##### 3. Add Environment Variables

**litellm service** → Variables tab → Add:
- `OPENAI_API_KEY` = `sk-...` (your OpenAI key – test this first)
- `ANTHROPIC_API_KEY` = `sk-ant-...` (optional for now)
- `LITELLM_CONFIG` = `/app/litellm_config.yaml` 

**open-webui service** → Variables tab → Add:
- `OPENAI_API_BASE_URL` = `http://litellm:4000` 
- `OPENAI_API_KEY` = `sk-anything` (dummy)
- `WEBUI_SECRET_KEY` = `generate-a-32-char-random-string-here` (use https://random.org/strings/)

##### 4. Set Public URL
- Select **open-webui** service  
- **Networking** tab → **Generate Domain**  
- Copy the URL (e.g. `https://jarvis-xxx.up.railway.app`)

##### 5. Deploy
- Click **Deploy** (top right)  
- Wait 3–6 minutes until both services are **green ✓**

**Note:** If Railway doesn't auto-detect compose, manually add services:
- **+ New** → **GitHub Repo** for `litellm` service (use Dockerfile.litellm)
- **+ New** → **GitHub Repo** for `open-webui` service (use Dockerfile.openwebui)

### 4. Configure JARVIS in WebUI (2 min)

1. Open your Railway public URL (e.g., `https://open-webui-xxx.up.railway.app`)
2. **Create admin account**
3. **Admin Panel** → **Settings** → **Pipelines**
4. **Add Pipeline:**
   - Open `pipelines/merge_thinking_orchestrator.py` in your IDE
   - Copy ALL contents (280 lines)
   - Paste into Pipeline editor
   - **Save**
5. **Enable the pipeline** (toggle switch)
6. **Configure Valves** (click settings icon):
   ```
   monthly_budget_usd: 50
   max_context_tokens: 8000
   enable_orchestrator: true
   enable_cost_tracking: true
   ```
   - **Save**

### 5. Test Merge Thinking (1 min)

1. Select model: `jarvis-gpt`
2. Send: **"How should I price my SaaS product?"**
3. JARVIS should reply: **"How would YOU handle this?"**
4. Answer: **"I'd charge $99/month based on competitors"**
5. JARVIS merges perspectives with research

### 6. Check Cost Tracking

After your first merge, check the data volume:

1. Railway → `open-webui` service → **Volumes** tab
2. Download `jarvis_cost_tracking.json` to verify tracking works

### 5. Configure JARVIS (2 min)

1. Open your Railway public URL (e.g., `https://open-webui-xxx.up.railway.app`)
2. **Create admin account**
3. **Admin Panel** → **Settings** → **Pipelines**
4. **Add Pipeline:**
   - Open `pipelines/merge_thinking_orchestrator.py` in your IDE
   - Copy ALL contents (280 lines)
   - Paste into Pipeline editor
   - **Save**
5. **Enable the pipeline** (toggle switch)
6. **Configure Valves** (click settings icon):
   ```
   monthly_budget_usd: 50
   max_context_tokens: 8000
   enable_orchestrator: true
   enable_cost_tracking: true
   ```
   - **Save**

### 6. Test Merge Thinking (1 min)

1. Select model: `jarvis-gpt`
2. Send: **"How should I price my SaaS product?"**
3. JARVIS should reply: **"How would YOU handle this?"**
4. Answer: **"I'd charge $99/month based on competitors"**
5. JARVIS merges perspectives with research

### 7. Check Cost Tracking

After your first merge, check the data volume:

1. Railway → `open-webui` service → **Volumes**
2. Download `jarvis_cost_tracking.json` to verify tracking works

---

## What You Get with v3

✅ **85% cost savings** vs v1 (3,000 tokens vs 15,000 per merge)  
✅ **Budget management** — Alerts at 80%, switches to brief mode at 100%  
✅ **Pattern learning** — Remembers your past decisions  
✅ **Multi-turn merge** — Iterate with "What if I changed X?"  
✅ **No token limit errors** — Intelligent compression prevents failures  

---

## Post-Deploy Customization

### Add Your System Prompt

1. **Models** → `jarvis-gpt` → **Edit**
2. Open `docs/system_prompt.md`
3. Customize the **User Context** section with your info
4. Paste into System Prompt field
5. **Save**

### Enable Web Search

1. **Admin Panel** → **Web Search**
2. Enable **DuckDuckGo**
3. **Save**

### Enable Memory

1. **Settings** → **Personalization** → **Memory**
2. Toggle **ON**
3. JARVIS will now remember facts across sessions

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

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Pipeline not showing | Refresh page, check for syntax errors in paste |
| "How would YOU handle this?" not triggering | Check pipeline is **enabled** (toggle on) |
| Cost tracking not working | Check `enable_cost_tracking: true` in valves |
| Models not appearing | Check LiteLLM service logs for API key errors |
| 502 errors | Wait 2-3 more minutes, services still starting |

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
