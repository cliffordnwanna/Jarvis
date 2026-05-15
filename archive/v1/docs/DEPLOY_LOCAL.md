# Deploy JARVIS Locally (Easiest Option)

If Railway/Render are giving you trouble, **run JARVIS locally** — it's the most reliable option for testing and development.

## Prerequisites

- Docker Desktop installed
- OpenAI API key

## Quick Start (5 minutes)

### 1. Create `.env` File

```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

### 2. Start Services

```bash
docker-compose up -d
```

This starts:
- **LiteLLM** on `http://localhost:4000`
- **Open WebUI** on `http://localhost:8080`

### 3. Wait for Services to Start

```bash
# Check logs
docker-compose logs -f

# Wait for these messages:
# litellm: "Uvicorn running on http://0.0.0.0:4000"
# open-webui: "Application startup complete"
```

Press `Ctrl+C` to exit logs.

### 4. Open JARVIS

1. Go to `http://localhost:8080`
2. Create your admin account
3. Start chatting!

## Upload v3 Orchestrator Pipeline

1. Click **profile icon** → **Admin Panel**
2. **Settings** → **Pipelines** → **+ Add Pipeline**
3. Copy contents of `pipelines/merge_thinking_orchestrator.py`
4. Paste and **Save**
5. **Enable** the pipeline (toggle switch)
6. Configure valves:
   - `monthly_budget_usd: 50`
   - `enable_orchestrator: true`
   - `enable_cost_tracking: true`

## Test Merge Thinking

1. Select model: `jarvis-gpt`
2. Ask: "How should I price my SaaS product?"
3. JARVIS replies: "How would YOU handle this?"
4. Answer with your approach
5. JARVIS merges perspectives

## Manage Services

```bash
# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f open-webui
docker-compose logs -f litellm

# Check status
docker-compose ps
```

## Troubleshooting

### Port Already in Use

If port 8080 or 4000 is already in use:

Edit `docker-compose.yml`:
```yaml
services:
  open-webui:
    ports:
      - "3000:8080"  # Change 8080 to 3000 (or any free port)
  
  litellm:
    ports:
      - "5000:4000"  # Change 4000 to 5000 (or any free port)
```

Then access at `http://localhost:3000`

### Models Not Appearing

1. Check LiteLLM logs:
   ```bash
   docker-compose logs litellm
   ```
2. Look for API key errors
3. Verify `.env` has correct `OPENAI_API_KEY`

### ChromaDB Errors

Local deployment has plenty of disk space, so ChromaDB should work fine. If you still get errors:

1. Stop services: `docker-compose down`
2. Remove volumes: `docker-compose down -v`
3. Start fresh: `docker-compose up -d`

## Advantages of Local Deployment

- ✅ **No cold starts** — instant responses
- ✅ **No disk limits** — ChromaDB works perfectly
- ✅ **Free** — only pay for API calls
- ✅ **Full control** — easy debugging
- ✅ **Privacy** — data stays on your machine

## When to Use Cloud Deployment

- Need 24/7 access from anywhere
- Want to share with team members
- Don't want to keep computer running

For cloud, I recommend:
1. **Render** (easier than Railway, better free tier)
2. **Railway** (if you upgrade volume to 5GB+)
3. **Hugging Face Spaces** (completely free, but slower)

---

## Next Steps

1. Test merge thinking locally
2. Verify cost tracking works
3. Customize system prompt
4. When satisfied, deploy to cloud using `DEPLOY_RENDER.md`
