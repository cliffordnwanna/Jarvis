"""
LLM streaming proxy — preserves the /llm/chat/completions endpoint from v2 (Fix 5).
Injects system prompt from rag/system_prompt.md and optionally RAG context.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.rag import build_rag_context, similarity_search

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE = "https://api.openai.com/v1"

_PROMPT_SENTINEL = "JARVIS v3 — system prompt"
_RAG_SENTINEL = "JARVIS v3 — retrieved memory"


def _load_system_prompt() -> str | None:
    env_prompt = os.getenv("JARVIS_SYSTEM_PROMPT")
    if env_prompt:
        return env_prompt.strip()

    repo_root = Path(__file__).resolve().parents[2]
    for candidate in ["rag/system_prompt.md", "rag/system_short.md"]:
        p = repo_root / candidate
        try:
            return p.read_text(encoding="utf-8").strip()
        except Exception:
            continue
    return None


def _inject_system_prompt(payload: dict) -> dict:
    prompt = _load_system_prompt()
    if not prompt:
        return payload

    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return payload

    for m in messages[:3]:
        if isinstance(m, dict) and m.get("role") == "system":
            if _PROMPT_SENTINEL in str(m.get("content", "")):
                return payload

    payload["messages"] = [
        {"role": "system", "content": f"{_PROMPT_SENTINEL}\n\n{prompt}"},
        *messages,
    ]
    return payload


async def _inject_rag(payload: dict, user_id: str | None = None) -> dict:
    if os.getenv("RAG_ENABLED", "true").lower() not in ("1", "true", "yes"):
        return payload
    if not os.getenv("SUPABASE_URL") or not os.getenv("OPENAI_API_KEY"):
        return payload

    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return payload

    for m in messages[:5]:
        if isinstance(m, dict) and _RAG_SENTINEL in str(m.get("content", "")):
            return payload

    last_user = None
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            last_user = str(m.get("content", "")).strip()
            break
    if not last_user or not user_id:
        return payload

    top_k = int(os.getenv("RAG_TOP_K", "5"))
    min_sim = float(os.getenv("RAG_MIN_SIMILARITY", "0.0"))
    max_chars = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "2000"))

    try:
        results = await similarity_search(user_id=user_id, query=last_user, top_k=top_k)
        results = [r for r in results if r.get("similarity", 0) >= min_sim]
        ctx = build_rag_context(results, max_chars=max_chars)
        if ctx:
            payload["messages"] = [
                {"role": "system", "content": f"{_RAG_SENTINEL}\n\n{ctx}"},
                *messages,
            ]
    except Exception:
        pass

    return payload


@router.post("/chat/completions")
async def proxy_chat_completions(request: Request):
    # Extract user_id from JWT header for RAG (best-effort, not blocking)
    user_id = None
    try:
        from backend.auth import get_current_user
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            user_id = await get_current_user(authorization=auth)
    except Exception:
        pass

    try:
        payload = await request.json()
    except Exception:
        payload = None

    if isinstance(payload, dict):
        payload = _inject_system_prompt(payload)
        payload = await _inject_rag(payload, user_id=user_id)
        body = json.dumps(payload).encode("utf-8")
    else:
        body = await request.body()

    async def stream():
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST",
                f"{OPENAI_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                content=body,
            ) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/models")
async def proxy_models():
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4o", "object": "model"},
            {"id": "gpt-4o-mini", "object": "model"},
        ],
    }
