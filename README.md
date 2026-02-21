# JARVIS Personal AI

The best personal AI in the world — browser + voice + memory + merge-thinking + multi-LLM (Claude, GPT, Llama, DeepSeek, etc.) — fully yours, always-on, no app needed.

## Quick Start

### 🏠 Local Development (Recommended - 5 min)

**Easiest and most reliable option for testing:**

1. **Clone and setup:**
   ```bash
   git clone <your-repo>
   cd Jarvis
   cp .env.example .env
   # Add your OPENAI_API_KEY to .env
   ```

2. **Start services:**
   ```bash
   docker-compose up -d
   ```

3. **Access JARVIS:**
   - Open WebUI: `http://localhost:8080`
   - Create admin account
   - Upload v3 orchestrator pipeline (see [DEPLOY_LOCAL.md](docs/DEPLOY_LOCAL.md))

**Full guide:** [docs/DEPLOY_LOCAL.md](docs/DEPLOY_LOCAL.md)

---

### ☁️ Cloud Deployment Options

#### Option 1: Railway ($5/month after $5 trial) ⭐ RECOMMENDED
- ✅ **Most reliable** — No hanging, crashes, or failures
- ✅ **Fast** — Excellent performance
- ✅ **Simple** — Deploy directly from GitHub in 10 minutes
- ✅ **Works everywhere** — Desktop, mobile, all platforms
- ✅ Voice features, persistent storage, auto-SSL
- 💰 **Cost:** $5 free trial, then $5-10/month
- ⏱️ **Total setup time:** 20 minutes

**Complete guide:** [docs/DEPLOY_RAILWAY_SIMPLE.md](docs/DEPLOY_RAILWAY_SIMPLE.md) ← **Start here!**

#### Option 2: Hugging Face Spaces (100% FREE Forever)
- ✅ **Completely free** (no credit card needed)
- ✅ 16GB RAM, 8 vCPU, 50GB disk
- ⚠️ **Slow/unstable** — May hang frequently
- ⚠️ Public by default, sleeps after 48h inactivity
- ⏱️ **Setup time:** 25 minutes

**Guide:** [docs/DEPLOY_HF_SPACES.md](docs/DEPLOY_HF_SPACES.md)

#### Option 2: Google Cloud Run (FREE $300 credit, then ~$5/month)
- ✅ Production-ready, auto-scaling
- ✅ $300 free credit (90 days)
- ✅ Always Free tier after credits
- ✅ Private by default
- ⏱️ **Cost after credits:** $5-7/month

**Full guide:** [docs/DEPLOY_FREE_TIER.md](docs/DEPLOY_FREE_TIER.md)

#### Option 3: Fly.io (FREE tier available)
- ✅ 3GB RAM free tier
- ✅ Simple deployment
- ✅ No credit card for free tier
- ⏱️ **Cost after free tier:** $5-10/month

**Full guide:** [docs/DEPLOY_FREE_TIER.md](docs/DEPLOY_FREE_TIER.md)

#### ~~Option 4: Render~~ (NOT RECOMMENDED - $19/month)
#### ~~Option 5: Railway~~ (NOT RECOMMENDED - Disk space issues)

**See [docs/DEPLOY_FREE_TIER.md](docs/DEPLOY_FREE_TIER.md) for complete comparison of all free/cheap hosting options.**

## Available Models

| Model Name | Provider | Best For |
|------------|----------|----------|
| `jarvis-gpt` | OpenAI | General use (test first) |
| `jarvis-gpt-mini` | OpenAI | Fast/cheap tasks |
| `jarvis-claude` | Anthropic | Deep reasoning |
| `jarvis-claude-fast` | Anthropic | Quick Claude tasks |
| `jarvis-router-*` | OpenRouter | Access 100+ models with one key |

## Features

- **Merge Thinking** — JARVIS asks your approach first, then merges perspectives honestly
- **Verify Mode** — Type `verify:` to fact-check any answer with tools + cross-model comparison
- **Persistent Memory** — Remembers your goals, preferences, and context across sessions
- **Voice I/O** — Talk via browser (works with AirPods on iPhone Safari)
- **Web Search** — DuckDuckGo integration for real-time info
- **Document RAG** — Upload and query PDFs/docs
- **Always-On** — Railway deployment means it's available 24/7 from any device

## Architecture

```
You (any device/browser)
        │
        ▼
   Open WebUI (UI + Auth + Memory + RAG + Voice)
        │
        ▼
   LiteLLM (Multi-LLM Proxy)
        │
        ▼
   OpenAI / Anthropic / OpenRouter / Ollama
```

## Docs

- [Product Requirements](docs/prd.md)
- [Implementation Plan](docs/plan.md)
- [Deployment Guide](docs/deployment.md)
