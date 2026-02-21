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

#### Option 1: Render (Easiest Cloud Deploy)
- ✅ Better free tier than Railway (1GB disk vs 500MB)
- ✅ Simpler setup, auto-detects Dockerfiles
- ✅ No volume configuration needed
- ⏱️ **Deploy time:** 10 minutes

**Full guide:** [docs/DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md)

#### Option 2: Railway (Advanced)
- ⚠️ Requires manual volume configuration (500MB → 5GB)
- ⚠️ More complex multi-service setup
- ✅ Good for production with paid plan
- ⏱️ **Deploy time:** 20 minutes

**Full guide:** [docs/DEPLOY_V3.md](docs/DEPLOY_V3.md)

**Note:** If you're experiencing "disk full" errors on Railway, use Render or local deployment instead.

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
