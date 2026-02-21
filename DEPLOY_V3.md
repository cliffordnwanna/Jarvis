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
2. **New Project** → **Empty Project**
3. Name it: `jarvis-personal-ai`

### 3. Deploy LiteLLM Service (5 min)

1. **New Service** → **GitHub Repo** → Select your `Jarvis` repo
2. **Settings:**
   - Service Name: `litellm`
   - Dockerfile Path: `Dockerfile.litellm`
3. **Variables** (click "New Variable"):
   ```
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   OPENROUTER_API_KEY=sk-or-...
   PORT=4000
   ```
4. **Deploy** (takes 3-4 min)
5. **Note the internal hostname** (e.g., `litellm.railway.internal`)

### 4. Deploy Open WebUI Service (5 min)

1. **New Service** → **GitHub Repo** → Same repo
2. **Settings:**
   - Service Name: `open-webui`
   - Dockerfile Path: `Dockerfile.openwebui`
3. **Variables:**
   ```
   OPENAI_API_BASE_URL=http://litellm.railway.internal:4000/v1
   OPENAI_API_KEY=sk-jarvis-railway
   WEBUI_SECRET_KEY=<RANDOM_32_CHAR_STRING>
   ENABLE_SIGNUP=true
   DEFAULT_MODELS=jarvis-gpt
   PORT=8080
   ```
4. **Networking** → **Generate Domain** (get public URL)
5. **Deploy** (takes 3-4 min)

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
