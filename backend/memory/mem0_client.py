"""
Mem0 OSS client — self-hosted against Supabase pgvector.
Owns: preferences, goals, projects, decisions, general facts.
Does NOT own: person/relationship memory (that stays in relationship_notes).

Deviations from the original spec, both confirmed by direct testing against
the installed mem0ai==2.2.1 before writing this file:

1. LLM provider is OpenAI (gpt-4o-mini), not Groq — GROQ_API_KEY was never
   configured in this project's .env. OpenAI is already paid for and wired.
   Switching to Groq later only requires changing the `llm` block below.

2. mem0ai 2.2.1's search()/get_all() reject a top-level `user_id` kwarg
   ("Top-level entity parameters ... are not supported... Use
   filters={'user_id': ...} instead") — confirmed via a live pre-flight
   call. add() still accepts user_id directly. Using filters= everywhere
   that reads, to match the installed version's real API.

3. history_db_path is set to ":memory:" rather than Mem0's own default
   (~/.mem0/history.db, a local SQLite file outside the project). Mem0's
   add() pulls the last 10 messages scoped to the same user/session from
   this file as extra context for every extraction call. On a long-lived
   local dev machine this file persists across unrelated test runs and
   script invocations — confirmed directly: unrelated facts from an
   earlier, completely different test (dark mode preference, a half
   marathon goal) kept reappearing as fresh duplicate ADDs during later,
   unrelated testing, because they were sitting in that shared history
   file. ":memory:" gives each process its own throwaway history, which
   still provides legitimate rolling context across requests *within* one
   backend run (the actual use case), while eliminating cross-run/cross-
   test contamination. On the VPS, a fresh deploy gets this for free
   either way since the file wouldn't persist across deploys regardless.

Mem0's internal operations (LLM + embedder calls) run synchronously in this
OSS implementation, so every call here is wrapped in
loop.run_in_executor to avoid blocking the FastAPI event loop.
"""
from __future__ import annotations
import asyncio
import os
from typing import Optional
from mem0 import Memory

USER_ID = "clifford"

_memory: Optional[Memory] = None


def _build_config() -> dict:
    """
    Build Mem0 config pointing at the existing Supabase pgvector instance.
    Uses OpenAI for both the LLM (fact extraction/conflict resolution) and
    the embedder (text-embedding-3-small, already used elsewhere in JARVIS).
    """
    db_url = os.getenv("DATABASE_URL", "")
    conn_string = (
        db_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )

    return {
        "vector_store": {
            "provider": "pgvector",
            "config": {
                "connection_string": conn_string,
                "collection_name": "jarvis_memories",
                "embedding_model_dims": 1536,
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o-mini",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "temperature": 0.1,
                "max_tokens": 2000,
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": "text-embedding-3-small",
            }
        },
        "history_db_path": ":memory:",
        "version": "v1.1"
    }


def get_memory() -> Memory:
    """Return singleton Memory instance. Initialised once at first call."""
    global _memory
    if _memory is None:
        _memory = Memory.from_config(_build_config())
    return _memory


async def remember(messages: list[dict], user_id: str = USER_ID) -> None:
    """
    Store memories from a conversation turn.

    user_id defaults to the module constant only for the one-off manual
    scripts (backend/scripts/*.py) that still call this directly against
    a known single-user dev environment. Every real request-path caller
    (main.py's /agent endpoint, voice's persistence path) passes the real
    authenticated user_id explicitly -- confirmed by checking every call
    site during the UUID/isolation audit.

    LIFECYCLE LAYER DISABLED (2026-10-08): apply_lifecycle() was wired in
    here to retire superseded facts (Mem0 OSS 2.2.x's own pipeline is
    ADD-only and never does this on its own -- confirmed by direct
    testing). On real testing against live data it worked for the one
    conflict it was meant to catch (Wema Bank -> Google) but ALSO
    wrongly retired 10 unrelated, still-valid memories in the same call
    (prior employer, career goal, all 5 projects, location, migration
    plan) -- _llm_supersedes() was over-triggering far beyond the
    intended mutable-fact categories. The deleted data was restored via
    backend/scripts/restore_deleted.py. Disabling the call here rather
    than deleting lifecycle.py: Mem0's plain ADD-only behavior (old and
    new facts coexisting) is a known, non-destructive gap -- it's a
    retrieval-quality problem, not data loss, and is the safer default
    until the supersession logic is redesigned and re-validated against
    real data without risk of further deletions.

    Never raises to the caller -- all errors are caught and logged.
    """
    def _sync_add():
        return get_memory().add(messages, user_id=user_id)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _sync_add)

        extracted = result.get("results", [])
        added = [r for r in extracted if r.get("event") == "ADD"]
        other = [r for r in extracted if r.get("event") != "ADD"]
        print(f"[mem0] extracted {len(extracted)} total: {len(added)} ADD, {len(other)} other")
        for r in extracted:
            print(f"  [{r.get('event')}] {r.get('memory', '')[:100]}")
    except Exception as e:
        print(f"[mem0] write error (non-fatal): {e}")


async def recall(query: str, user_id: str = USER_ID, top_k: int = 5) -> str:
    """
    Retrieve relevant long-term memories for a query.
    Returns formatted string for injection into context, or empty string.

    Uses top_k, not limit -- confirmed via inspect.signature(Memory.search)
    that `limit` is not a real parameter (it silently falls into **kwargs
    and is ignored, always returning up to the top_k=20 default) while
    top_k is the one that actually constrains result count.

    user_id defaults to the module constant for the same reason as
    remember() above -- real callers always pass the authenticated value.
    """
    def _sync_search():
        return get_memory().search(query, filters={"user_id": user_id}, top_k=top_k)

    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _sync_search)
        memories = results.get("results", [])
        if not memories:
            return ""

        lines = []
        for m in memories:
            text = m.get("memory", "")
            created = m.get("created_at", "")
            if created:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    date_str = dt.strftime("%b %Y")
                except Exception:
                    date_str = created[:7]
                lines.append(f"- [{date_str}] {text}")
            else:
                lines.append(f"- {text}")
        return "\n".join(lines)
    except Exception as e:
        print(f"[mem0] read error (non-fatal): {e}")
        return ""


async def get_all() -> list:
    """Return all stored memories — used by debug endpoint."""
    def _sync_get_all():
        return get_memory().get_all(filters={"user_id": USER_ID}).get("results", [])

    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_get_all)
    except Exception as e:
        print(f"[mem0] get_all error: {e}")
        return []


async def delete_all(user_id: str) -> int:
    """
    Delete every stored memory for user_id via direct Postgres, not
    get_all(). Confirmed by direct testing that get_all() undercounts real
    rows in this config (reported 20 when 34 actually existed) -- using it
    to drive deletion would leave orphaned rows behind.

    user_id is now a required parameter (previously hardcoded to the
    module's old USER_ID constant) -- fixed during the UUID/isolation
    audit. Caller must pass the real authenticated UUID explicitly.
    """
    def _sync_delete_all():
        import psycopg
        conn_string = (
            os.getenv("DATABASE_URL", "")
            .replace("postgresql+asyncpg://", "postgresql://")
            .replace("postgresql+psycopg2://", "postgresql://")
        )
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM jarvis_memories WHERE payload->>'user_id' = %s",
                    (user_id,),
                )
                deleted = cur.rowcount
                conn.commit()
                return deleted

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_delete_all)


async def get_all_authoritative(user_id: str) -> list:
    """
    List every stored memory for user_id via direct Postgres -- the
    authoritative source, not get_all(). Used by /debug/memories.

    user_id is now required (previously hardcoded) -- same fix as
    delete_all() above, from the UUID/isolation audit.
    """
    def _sync_query():
        import psycopg
        conn_string = (
            os.getenv("DATABASE_URL", "")
            .replace("postgresql+asyncpg://", "postgresql://")
            .replace("postgresql+psycopg2://", "postgresql://")
        )
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        payload->>'data'       AS memory,
                        payload->>'user_id'    AS user_id,
                        payload->>'created_at' AS created_at
                    FROM jarvis_memories
                    WHERE payload->>'user_id' = %s
                    ORDER BY (payload->>'created_at') DESC
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
                return [
                    {"id": str(r[0]), "memory": r[1], "user_id": r[2], "created_at": r[3]}
                    for r in rows
                ]

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_query)
