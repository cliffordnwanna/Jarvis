"""
LangChain tools exposing Mem0 to the JARVIS agent.

Routing rule (in system prompt):
- Person/relationship questions -> use existing hybrid_search_notes_tool
- General facts/preferences/goals/projects/decisions -> use these Mem0 tools

The agent must not use these tools to store person-entity data
(names, workplaces, relationships) -- that belongs in relationship_notes.
"""
from __future__ import annotations
import asyncio
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from backend.memory.mem0_client import get_memory, remember


@tool
async def search_my_memory(query: str, user_id: Annotated[str, InjectedState("user_id")]) -> str:
    """
    Search Clifford's long-term memory for preferences, goals, projects,
    decisions, and general facts.

    Use this tool when the question is about:
    - Clifford's preferences ("what coding languages do I prefer")
    - His goals ("what are my current goals")
    - Project decisions ("what did I decide about UpJobs")
    - General facts not about a specific person ("where do I work")
    - Past decisions Clifford mentioned

    Do NOT use this for questions about specific people (sister, colleagues,
    friends) -- use hybrid_search_notes_tool for those instead.
    """
    def _sync():
        # mem0ai's search() rejects a top-level user_id kwarg in the
        # installed version; filters={"user_id": ...} is the real API.
        # top_k, not limit, is the real result-count parameter -- confirmed
        # via inspect.signature(Memory.search); limit silently does nothing.
        results = get_memory().search(query, filters={"user_id": user_id}, top_k=5)
        memories = [r["memory"] for r in results.get("results", [])]
        if not memories:
            return "No relevant memories found."
        return "\n".join(f"- {m}" for m in memories)

    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync)
    except Exception as e:
        return f"Memory search error: {e}"


@tool
async def save_to_memory(fact: str, user_id: Annotated[str, InjectedState("user_id")]) -> str:
    """
    Save an important fact, preference, goal, or decision to long-term memory.

    Use this when Clifford:
    - States a preference ("I prefer X over Y")
    - Makes a decision ("I decided to use X for Y")
    - Sets a goal ("I want to achieve X by Y")
    - Shares important context about his work or life

    Do NOT use this for person-specific details -- those go in
    relationship_notes via the add_note_for_person tool.

    Always confirm to Clifford when something has been saved.
    """
    # Routed through remember() rather than calling get_memory().add()
    # directly, so there's one single write path into Mem0 to reason about
    # -- not because of lifecycle logic. The lifecycle/superseding layer
    # (apply_lifecycle) this comment used to describe was removed from
    # remember() after it wrongly retired 10 unrelated memories in testing
    # (see mem0_client.py's remember() docstring) -- Mem0 is ADD-only here
    # now, deliberately. Current-state facts that can change (employer,
    # location, etc.) belong in memory_files, not here, precisely because
    # Mem0 has no safe update/supersede mechanism.
    try:
        await remember([{"role": "user", "content": fact}], user_id=user_id)
        return f"Saved to memory: {fact}"
    except Exception as e:
        return f"Memory save error: {e}"
