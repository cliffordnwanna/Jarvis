# JARVIS Personal AI

The best personal AI in the world — browser + voice + memory + merge-thinking + multi-LLM (Claude, GPT, Llama, DeepSeek, etc.) — fully yours, always-on, no app needed.

## Quick Start (Local)

```bash
cp .env.example .env
# Edit .env with your API keys (at minimum: OPENAI_API_KEY)

docker compose up -d
```

Open **http://localhost:8080** → Create admin account → Select `jarvis-gpt` → Start chatting.

## Quick Start (Railway)

See [docs/deployment.md](docs/deployment.md) for full Railway deployment guide.

**TL;DR:** Deploy two services from this repo — `Dockerfile.litellm` (LLM proxy) and `Dockerfile.openwebui` (UI) — set your API keys, and you're live.

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
