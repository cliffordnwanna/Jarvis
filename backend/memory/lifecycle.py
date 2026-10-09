"""
JARVIS Memory Lifecycle Layer.

Operates on memories AFTER Mem0 has extracted and stored them.
Handles the one thing Mem0 OSS 2.2.x doesn't: current-state supersession.
Confirmed via direct testing: mem0ai==2.2.1's OSS pipeline is ADD-only —
telling it a fact that contradicts an existing memory produces a second,
independent ADD, never an UPDATE or DELETE of the original.

Mem0 continues to own: extraction, embedding, storage, retrieval.
This layer owns: detecting when a new memory supersedes an existing one.

Mutable facts (only one current value valid):
  employer, job title, location, relationship status, current project status

All other facts are append-only (events, decisions, experiences, history).
Mutability is judged per-memory by an LLM call (_llm_is_mutable), not a
keyword list -- see deviation #2 below for why.

Two deviations from the original spec, both confirmed necessary by direct
testing before/while writing this file, not by speculation:

1. search() score values for genuinely relevant candidates vary widely by
   query phrasing in this Mem0/pgvector config -- observed anywhere from
   0.56 down to 0.27 for the SAME real conflict (Wema Bank vs Google)
   depending on exact wording. Any fixed score floor risks filtering out
   the one candidate this layer exists to catch. The score pre-filter is
   dropped entirely -- every search() candidate goes to the LLM judgment
   step, which is the real gate per the architecture's own stated design
   ("similarity only generates candidates; LLM judgment is the real gate").

2. The original keyword-based _is_likely_mutable() checked for first-person
   phrases ("i now work", "i left") and bare category words ("employer",
   "job title"). It never matched anything: Mem0 always rewrites extracted
   facts into third person ("Clifford now works at Google..."), and real
   extracted phrasing doesn't contain bare category words either. Confirmed
   via a live test that this silently skipped a genuine Wema->Google
   conflict end to end. Replaced with a second LLM judgment call
   (_llm_is_mutable) -- one extra cheap gpt-4o-mini call per newly
   extracted memory, which is what actually generalizes across Mem0's
   variable extraction phrasing instead of guessing at keywords.
"""
from __future__ import annotations
import asyncio
import os
from typing import Optional
from openai import AsyncOpenAI

_llm = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def _llm_is_mutable(memory_text: str) -> bool:
    """Does this memory describe a current-state fact that can change over time?"""
    try:
        resp = await _llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Does this fact describe a CURRENT STATE that can change "
                        "(employer, location, job title, relationship status, "
                        "current project) -- or is it a permanent/historical fact "
                        "(event, decision, experience, achievement)?\n"
                        "Reply with exactly one word: MUTABLE or PERMANENT"
                    ),
                },
                {"role": "user", "content": memory_text},
            ],
            max_tokens=5,
            temperature=0,
        )
        return "MUTABLE" in resp.choices[0].message.content.strip().upper()
    except Exception as e:
        print(f"[lifecycle] mutability judgment error: {e}")
        return False  # safe default: don't retire if unsure


async def _llm_supersedes(existing: str, new: str) -> bool:
    """
    Ask gpt-4o-mini: does the new fact supersede/replace the existing one?
    Returns True if new makes existing outdated.
    Returns False if both can be true simultaneously.
    """
    try:
        resp = await _llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Does the NEW fact make the EXISTING fact outdated/incorrect? "
                        "Reply with exactly one word: SUPERSEDES or COMPLEMENTARY.\n"
                        "SUPERSEDES = new replaces old (only new is currently true).\n"
                        "COMPLEMENTARY = both can be true simultaneously."
                    ),
                },
                {
                    "role": "user",
                    "content": f"EXISTING: {existing}\nNEW: {new}",
                },
            ],
            max_tokens=5,
            temperature=0,
        )
        verdict = resp.choices[0].message.content.strip().upper()
        return "SUPERSEDES" in verdict
    except Exception as e:
        print(f"[lifecycle] LLM judgment error: {e}")
        return False  # safe default: don't delete if unsure


async def apply_lifecycle(
    new_memory_text: str,
    new_memory_id: str,
    mem0_client,
    user_id: str,
) -> None:
    """
    Apply lifecycle policy to a single newly-extracted memory.
    Called AFTER Mem0 has already stored the new memory.

    If the new memory supersedes an existing one:
    - Delete the existing one (confirmed working in pre-flight)
    - Log the retirement

    Never deletes the new memory itself.
    Never raises -- all errors are logged and swallowed.
    """
    if not await _llm_is_mutable(new_memory_text):
        return  # append-only fact, nothing to do

    # Find candidates from existing memories. limit=5 (the original value)
    # was confirmed too narrow by direct testing: against the real Wema
    # Bank -> Google conflict, the genuinely superseded candidate ranked
    # #10 by score, outside a 5-result window -- the LLM judgment step
    # never got a chance to see it. 20 is comfortably wider than any
    # mutable-fact collision observed so far.
    def _sync_search():
        return mem0_client.search(
            new_memory_text,
            filters={"user_id": user_id},
            limit=20,
        )

    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _sync_search)
        candidates = results.get("results", [])
    except Exception as e:
        print(f"[lifecycle] search error: {e}")
        return

    for candidate in candidates:
        candidate_id = candidate.get("id")
        candidate_text = candidate.get("memory", "")

        # Never retire the memory we just added
        if candidate_id == new_memory_id:
            continue

        if not candidate_text:
            continue

        # No score pre-filter -- confirmed by pre-flight testing that
        # relevant candidates in this config score ~0.52-0.56, below any
        # sensible fixed floor. Every candidate goes to the LLM judgment
        # step, which is the real gate.
        supersedes = await _llm_supersedes(candidate_text, new_memory_text)

        if supersedes:
            def _sync_delete(mid=candidate_id):
                mem0_client.delete(memory_id=mid)

            try:
                await loop.run_in_executor(None, _sync_delete)
                print(
                    f"[lifecycle] retired superseded memory {candidate_id}: "
                    f"{candidate_text[:80]}..."
                )
            except Exception as e:
                print(f"[lifecycle] delete failed for {candidate_id}: {e}")
