"""
LLM proxy — routes AI SDK calls through Python to bypass corporate DNS restrictions.
All completions go to OpenAI. OpenAI is also used for RAG embeddings.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.rag import build_rag_context, similarity_search

router = APIRouter(prefix="/llm", tags=["llm"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE = "https://api.openai.com/v1"

_PROMPT_SENTINEL = "JARVIS v2 — short system prompt"
_RAG_SENTINEL = "JARVIS v2 — retrieved memory"


def _load_system_prompt() -> str | None:
    """
    Load the canonical short system prompt from rag/system_short.md.

    Note: In Docker, ensure the rag/ folder is copied into the image.
    """
    env_prompt = os.getenv("JARVIS_SYSTEM_PROMPT")
    if env_prompt:
        return env_prompt.strip()

    repo_root = Path(__file__).resolve().parents[2]
    prompt_path = repo_root / "rag" / "system_short.md"
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except Exception:
        return None


def _inject_system_prompt(payload: dict) -> dict:
    prompt = _load_system_prompt()
    if not prompt:
        return payload

    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return payload

    for m in messages[:3]:
        if isinstance(m, dict) and m.get("role") == "system" and isinstance(m.get("content"), str):
            if _PROMPT_SENTINEL in m["content"]:
                return payload

    payload["messages"] = [{"role": "system", "content": f"{_PROMPT_SENTINEL}\n\n{prompt}"}, *messages]
    return payload


async def _inject_rag(payload: dict) -> dict:
    # Default OFF to avoid embedding spend before Supabase + ingestion are set up.
    if os.getenv("RAG_ENABLED", "false").lower() not in ("1", "true", "yes"):
        return payload
    if not os.getenv("SUPABASE_URL"):
        return payload
    if not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        return payload
    if not os.getenv("OPENAI_API_KEY"):
        return payload

    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return payload

    # Avoid duplicating on retries.
    for m in messages[:5]:
        if isinstance(m, dict) and m.get("role") == "system" and isinstance(m.get("content"), str):
            if _RAG_SENTINEL in m["content"]:
                return payload

    # Use the latest user message for retrieval (cheapest, most relevant).
    last_user = None
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user" and isinstance(m.get("content"), str):
            last_user = m["content"].strip()
            break
    if not last_user:
        return payload

    user_id = os.getenv("RAG_USER_ID", "default")
    top_k = int(os.getenv("RAG_TOP_K", "5"))
    min_sim = float(os.getenv("RAG_MIN_SIMILARITY", "0.0"))
    max_chars = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "2000"))

    try:
        results = await similarity_search(user_id=user_id, query=last_user, top_k=top_k)
        results = [r for r in results if isinstance(r.get("similarity"), (int, float)) and r["similarity"] >= min_sim]
        ctx = build_rag_context(results, max_chars=max_chars)
        if not ctx:
            return payload
        payload["messages"] = [{"role": "system", "content": f"{_RAG_SENTINEL}\n\n{ctx}"}, *messages]
        return payload
    except Exception:
        # Retrieval should never break chat.
        return payload


def _route(model: str) -> tuple[str, str]:
    return OPENAI_BASE, OPENAI_API_KEY


@router.post("/chat/completions")
async def proxy_chat_completions(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = None

    if isinstance(payload, dict):
        payload = _inject_system_prompt(payload)
        payload = await _inject_rag(payload)
        body = json.dumps(payload).encode("utf-8")
        model = str(payload.get("model", "") or "")
    else:
        body = await request.body()
        try:
            model = json.loads(body).get("model", "")
        except Exception:
            model = ""

    base_url, api_key = _route(model)

    async def stream():
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                content=body,
            ) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/models")
async def proxy_models():
    """Return supported models."""
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4o-mini", "object": "model"},
            {"id": "gpt-4o", "object": "model"},
        ],
    }
