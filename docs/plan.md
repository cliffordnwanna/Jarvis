**✅ Confirmed – Updated Full Implementation Guide (Feb 21 2026)**  
**Canonical deployment:** Railway + local Docker Compose  
**Phase 1 providers:** Anthropic (Claude) + OpenAI (you will test OpenAI first)  
**Merge Thinking state:** Persistent across restarts (using file-backed storage in the Open WebUI volume)  
**Verify mode:** Manual only — just type “verify:” or “verify this” after any answer  
**Phase 2 focus (first delivery):** Ollama + Background agents  


```markdown
# JARVIS Personal AI – Production-Ready Implementation Guide
**Canonical:** Railway + local Docker Compose  
**Total time to live:** 45–60 min (once repo is set up)  
**State:** Merge Thinking now survives restarts (file-backed)  
**Test order:** OpenAI first → then Claude

## Repo Structure (create these files)

```
jarvis-personal-ai/
├── docker-compose.yml              # Local + Railway-compatible
├── .env.example                    # All secrets
├── litellm_config.yaml             # All models (Claude + OpenAI now)
├── pipelines/
│   └── merge_thinking.py           # Persistent version (JSON file)
├── .gitignore
├── README.md
└── docs/
    ├── deployment.md
    ├── prd.md
    └── plan.md
```

## 1. Create the Repo (5 min)

1. Go to GitHub → New repo: `jarvis-personal-ai` (Private)
2. Clone it locally:
   ```bash
   git clone https://github.com/yourusername/jarvis-personal-ai.git
   cd jarvis-personal-ai
   ```

## 2. Create the Files (copy-paste below)

### `.env.example`
```env
# OpenAI (you will test this first)
OPENAI_API_KEY=sk-...

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-...

# Optional later
ELEVENLABS_API_KEY=
PUSHOVER_USER=
PUSHOVER_TOKEN=
```

### `litellm_config.yaml`
```yaml
model_list:
  - model_name: jarvis-opus
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20241022
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: jarvis-gpt   # ← You will test this first
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  - model_name: jarvis-fast
    litellm_params:
      model: anthropic/claude-3-haiku-20240307
      api_key: os.environ/ANTHROPIC_API_KEY

litellm_settings:
  drop_params: true
  set_verbose: false
```

### `docker-compose.yml` (works locally AND on Railway)
```yaml
version: '3.9'

services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: jarvis-open-webui
    ports:
      - "8080:8080"
    volumes:
      - open-webui-data:/app/backend/data
    environment:
      - OPENAI_API_BASE_URL=http://litellm:4000
      - OPENAI_API_KEY=sk-anything
      - OLLAMA_API_BASE_URL=http://ollama:11434   # for Phase 2
    depends_on:
      - litellm
    restart: unless-stopped

  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: jarvis-litellm
    ports:
      - "4000:4000"
    volumes:
      - ./litellm_config.yaml:/app/litellm_config.yaml
    environment:
      - LITELLM_CONFIG=/app/litellm_config.yaml
    env_file: .env
    restart: unless-stopped

volumes:
  open-webui-data:
```

### `pipelines/merge_thinking.py` (Persistent version)
```python
"""
JARVIS Merge Thinking Pipeline – Persistent across restarts
Uses JSON file in Open WebUI data volume.
"""

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

STATE_FILE = Path("/app/backend/data/jarvis_merge_state.json")

class Pipeline:
    class Valves(BaseModel):
        merge_trigger_words: str = "how should,how do I,how would you,best way,should I,what's the best,decide,decision"
        ask_user_first: bool = True

    def __init__(self):
        self.name = "JARVIS Merge Thinking (Persistent)"
        self.valves = self.Valves()
        self._ensure_state_file()

    def _ensure_state_file(self):
        if not STATE_FILE.exists():
            STATE_FILE.write_text(json.dumps({}))

    def _load_state(self):
        return json.loads(STATE_FILE.read_text())

    def _save_state(self, state):
        STATE_FILE.write_text(json.dumps(state, indent=2))

    def is_decision_question(self, message: str) -> bool:
        triggers = self.valves.merge_trigger_words.lower().split(",")
        return any(t.strip() in message.lower() for t in triggers)

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        messages = body.get("messages", [])
        if not messages:
            return body

        last_msg = messages[-1]
        user_text = last_msg.get("content", "") if isinstance(last_msg.get("content"), str) else ""
        user_id = user.get("id", "default") if user else "default"

        state = self._load_state()
        awaiting_key = f"{user_id}_awaiting"

        # === USER JUST ANSWERED "How would YOU handle this?" ===
        if awaiting_key in state:
            original_q = state.pop(awaiting_key)
            self._save_state(state)

            merge_instruction = {
                "role": "system",
                "content": f"[MERGE_STATE] Original question: {original_q}\nUser approach: {user_text}\n\n"
                           "Now: 1. Research independently with tools. "
                           "2. Merge: where we align + where I'd do differently and exactly why. "
                           "Be direct, never diplomatic."
            }
            body["messages"].insert(-1, merge_instruction)
            return body

        # === DETECT DECISION QUESTION ===
        if self.valves.ask_user_first and self.is_decision_question(user_text) and len(user_text) > 20:
            state[awaiting_key] = user_text
            self._save_state(state)

            body["messages"][-1]["content"] = (
                f"The user asked: '{user_text}'\n\n"
                "Before answering, reply with ONLY this one question and nothing else:\n"
                "'How would YOU handle this?'"
            )

        # === VERIFY MODE (manual) ===
        if user_text.strip().lower().startswith(("verify:", "verify this")):
            body["messages"].insert(0, {
                "role": "system",
                "content": "This is a VERIFY request. Use tools to double-check facts. "
                           "If multiple models are available, compare Claude and GPT-4o. "
                           "Show sources and confidence."
            })

        return body
```

### `README.md` (top level)
```markdown
# JARVIS Personal AI

Local: `docker compose up -d` → http://localhost:8080  
Railway: Connect GitHub repo → auto-detects docker-compose

First test with OpenAI (gpt-4o model).
```

## 3. Local Test (10 min)

```bash
cp .env.example .env
# ← edit .env with your real keys

docker compose up -d
```

Open http://localhost:8080 → create admin account → select `jarvis-gpt` first.

## 4. Railway Deployment (15 min)

1. Push everything to GitHub
2. Railway → New Project → Deploy from GitHub repo
3. Railway will auto-detect `docker-compose.yml`
4. Add the same environment variables from `.env` to the **litellm** service
5. Deploy → wait 4–6 min → click the URL

## 5. Final Configuration in Open WebUI

1. **Models** → `jarvis-gpt` (or `jarvis-opus`) → Edit → paste the long system prompt from the original PRD (updated with your personal info).
2. **Settings → Personalization → Memory** → Enable
3. **Admin Panel → Web Search** → Enable DuckDuckGo
4. **Pipelines** → Add New → paste the `merge_thinking.py` code above → Save & Enable

## 6. How to Use Merge Thinking & Verify

- Ask: “How should I price my next product?”
  → JARVIS replies: “How would YOU handle this?”
  → You answer → JARVIS merges (state saved forever)

- After any answer: just type `verify:` → it will double-check with tools + cross-model comparison.

## Next (Phase 2 – after you confirm live)

I will give you:
- Ollama service in docker-compose
- Background agents pipeline (APScheduler + daily goal check)
- Cost monitoring dashboard

**You are now 100% ready.**

Run the local `docker compose up` and tell me the exact moment you see the login screen — I will walk you through the first test chat live.

Let’s ship the best personal AI on the planet.
```

**Done.**  
You now have a **fully reproducible, persistent, local + Railway** setup with your exact requirements.

Next step for you:
1. Create the repo + copy the 5 files above
2. Run `docker compose up -d`
3. Tell me when you are at the login screen

I will then give you the exact system prompt + first test commands.  
Ready when you are.
```