import json
import os
from dotenv import load_dotenv
load_dotenv()  # loads .env from cwd before anything else reads os.getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis

from backend.routers import context, llm, memory, nudges

app = FastAPI(title="JARVIS v2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(context.router)
app.include_router(llm.router)
app.include_router(memory.router)
app.include_router(nudges.router)

# Mount LangGraph agent via CopilotKit (optional — graceful fallback if pkg missing)
try:
    from copilotkit import langraph
    from backend.agent import build_agent

    langraph.add_fastapi_endpoint(
        app=app,
        path="/agent",
        graph=build_agent(),
        config_schema=None,
    )
    print("CopilotKit /agent endpoint mounted.")
except Exception as e:
    print(f"CopilotKit agent endpoint skipped: {e}")
    print("Backend will run without /agent. REST endpoints (/context, /nudges, /memory) still work.")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0"}


@app.get("/world-state")
async def get_world_state():
    """Return the latest enriched world state (built by /context pipeline)."""
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    try:
        try:
            raw = await r.get("world_state")
        except Exception:
            return {
                "status": "redis_down",
                "message": "Redis is not reachable. Start Redis (docker-compose) and POST /context.",
            }
        if not raw:
            return {"status": "empty", "message": "No world state yet — POST to /context first"}
        return json.loads(raw)
    finally:
        await r.aclose()
