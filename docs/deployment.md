# JARVIS – Railway Deployment Guide

## Architecture on Railway

Railway doesn't support multi-container `docker-compose.yml` natively. Instead, you deploy **two separate services** in one Railway project that communicate via Railway's internal networking.

```
┌─────────────────────────────────────────────┐
│              Railway Project                 │
│                                              │
│  ┌──────────────┐    ┌───────────────────┐  │
│  │   LiteLLM    │◄───│   Open WebUI      │  │
│  │  (Proxy)     │    │   (Frontend)      │  │
│  │  Port 4000   │    │   Port 8080       │  │
│  └──────────────┘    └───────────────────┘  │
│         ▲                                    │
│         │ API calls                          │
│  ┌──────┴───────────────────────────────┐   │
│  │  OpenAI / Anthropic / OpenRouter     │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## Step-by-Step Deployment

### 1. Push to GitHub

```bash
git add -A
git commit -m "Initial JARVIS setup"
git push origin main
```

### 2. Create Railway Project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Choose **Empty Project**

### 3. Deploy LiteLLM Service (first)

1. In your Railway project → **New Service** → **GitHub Repo** → select your `Jarvis` repo
2. **Settings:**
   - **Service Name:** `litellm`
   - **Root Directory:** `/` (leave default)
   - **Dockerfile Path:** `Dockerfile.litellm`
3. **Variables** (add these):
   ```
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   OPENROUTER_API_KEY=sk-or-...
   PORT=4000
   ```
4. **Networking:**
   - Railway auto-assigns an internal hostname like `litellm.railway.internal`
   - Note this hostname — you'll need it for Open WebUI
5. Click **Deploy**

### 4. Deploy Open WebUI Service (second)

1. In the same project → **New Service** → **GitHub Repo** → same repo
2. **Settings:**
   - **Service Name:** `open-webui`
   - **Dockerfile Path:** `Dockerfile.openwebui`
3. **Variables:**
   ```
   OPENAI_API_BASE_URL=http://litellm.railway.internal:4000/v1
   OPENAI_API_KEY=sk-jarvis-railway
   WEBUI_SECRET_KEY=<generate-a-random-string>
   ENABLE_SIGNUP=true
   DEFAULT_MODELS=jarvis-gpt
   PORT=8080
   ```
4. **Networking:**
   - Click **Generate Domain** to get a public URL (e.g., `open-webui-xxx.up.railway.app`)
5. Click **Deploy**

### 5. Verify

1. Wait 3–5 minutes for both services to build and start
2. Open the public URL from step 4
3. Create your admin account
4. Go to model selector → you should see `jarvis-gpt`, `jarvis-claude`, etc.
5. Send a test message

### 6. Post-Deploy Configuration

In Open WebUI (logged in as admin):

1. **Models** → Select `jarvis-gpt` → Edit → Paste your system prompt
2. **Settings → Personalization → Memory** → Enable
3. **Admin Panel → Web Search** → Enable DuckDuckGo
4. **Pipelines** → Add New → Paste contents of `pipelines/merge_thinking.py` → Save & Enable

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Open WebUI can't reach LiteLLM | Check `OPENAI_API_BASE_URL` uses `litellm.railway.internal` (not localhost) |
| Models not showing | Check LiteLLM logs; verify API keys are set in LiteLLM service variables |
| 502 errors | Service still starting — wait 2-3 more minutes |
| LiteLLM health fails | Ensure `PORT=4000` is set and Dockerfile.litellm is selected |

## Cost Estimate

- **Railway:** ~$5-10/month (usage-based, first $5 free)
- **OpenAI API:** ~$5-20/month depending on usage
- **OpenRouter:** Pay-per-token, often cheaper than direct API
- **Total:** ~$10-30/month for always-on personal AI

## Local Development

For local testing, use docker-compose:

```bash
cp .env.example .env
# Edit .env with your real keys
docker compose up -d
# Open http://localhost:8080
```
