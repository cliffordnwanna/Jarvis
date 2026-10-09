"""
Layered context builder for JARVIS.
Assembles the system prompt from priority-ordered layers within a token budget.

Phase 2 will add Mem0 memories to Layer 5 (currently empty slot).
Phase 3 will add real conversation_summaries data to Layer 6 (the table
does not exist yet — this layer safely returns nothing until then).

Layer 7 (recent messages) is NOT assembled here — LangGraph replays it
from the PostgresSaver checkpointer via thread_id.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import tiktoken

from backend.agent import BASE_SYSTEM_PROMPT

_enc = tiktoken.encoding_for_model("gpt-4o")


def _count_tokens(text: str) -> int:
    return len(_enc.encode(text))


@dataclass
class LayerResult:
    name: str
    included: bool
    token_count: int
    reason: str = ""  # why excluded, if not included


@dataclass
class ContextResult:
    text: str
    total_tokens: int
    layers: list[LayerResult] = field(default_factory=list)

    def log_summary(self) -> str:
        lines = [f"Context: {self.total_tokens} tokens"]
        for l in self.layers:
            status = "✓" if l.included else "✗"
            lines.append(
                f"  {status} {l.name} ({l.token_count}t)"
                + (f" — {l.reason}" if l.reason else "")
            )
        return "\n".join(lines)


async def build_context(
    user_id: str,
    conversation_id: str,
    current_message: str,
    world_state: Optional[dict] = None,
    supabase=None,
    # BASE_SYSTEM_PROMPT alone is ~3437 tokens (confirmed via _count_tokens)
    # and grows over time as tool-use rules are added -- the old default of
    # 3000 meant the ENTIRE instructions layer (all tool rules, memory
    # rules) could silently fail its own budget check and be dropped from
    # the real prompt, since min_tokens=0 only lowers the bar to ATTEMPT a
    # layer, it does not exempt it from the tc > remaining check in
    # _try_add(). Raised with real headroom for profile/world_state/goals/
    # memory/memory_index on top, confirmed via direct testing that this
    # was a live risk (not hypothetical) with the real BASE_SYSTEM_PROMPT.
    max_tokens: int = 6000,
    profile_text: Optional[str] = None,
    world_state_text: Optional[str] = None,
) -> ContextResult:
    """
    Build the layered system prompt within the token budget.
    Layers are added in priority order; lower-priority layers drop out first.

    profile_text / world_state_text let a caller that already has richer,
    pre-formatted text (e.g. main.py's detailed weather/rain-probability and
    home/work route-tool-hint construction) supply it directly for layers
    2/3 instead of this module's simpler built-in formatting. When omitted,
    layers 2/3 fall back to querying/formatting from `supabase`/`world_state`
    themselves — this is what the /debug/context endpoint exercises.
    """
    layers: list[LayerResult] = []
    sections: list[str] = []
    remaining = max_tokens

    def _try_add(name: str, content: Optional[str], min_tokens: int = 50, required: bool = False) -> bool:
        nonlocal remaining
        if not content or not content.strip():
            layers.append(LayerResult(name, False, 0, "empty"))
            return False
        tc = _count_tokens(content)
        # required=True (the instructions layer only) bypasses the budget
        # check entirely rather than just lowering the attempt threshold --
        # min_tokens=0 alone does NOT exempt a layer from tc > remaining,
        # which previously let the entire system prompt silently drop when
        # BASE_SYSTEM_PROMPT outgrew the token budget (confirmed as a real,
        # not hypothetical, failure mode). The core instructions must never
        # be silently absent; every other layer still competes for budget
        # normally and can legitimately be dropped.
        if not required and (tc > remaining or remaining < min_tokens):
            layers.append(LayerResult(name, False, tc, "budget exceeded"))
            return False
        sections.append(content)
        layers.append(LayerResult(name, True, tc))
        remaining -= tc
        return True

    # Layer 1: Base instructions — always included, never truncated
    _try_add("instructions", BASE_SYSTEM_PROMPT, required=True)

    # Layer 2: User profile — caller-supplied formatted text takes priority;
    # falls back to real users table columns only
    if profile_text is not None:
        _try_add("profile", profile_text)
    elif supabase:
        profile = _get_user_profile(user_id, supabase)
        _try_add("profile", profile)
    else:
        layers.append(LayerResult("profile", False, 0, "no supabase client"))

    # Layer 3: World state — caller-supplied formatted text takes priority;
    # falls back to this module's simpler formatting of the raw dict
    if world_state_text is not None:
        _try_add("world_state", world_state_text)
    elif world_state:
        ws_text = _format_world_state(world_state)
        _try_add("world_state", ws_text)
    else:
        layers.append(LayerResult("world_state", False, 0, "not provided"))

    # Layer 4: Active goals — real goals table columns only
    if supabase:
        goals_text = _get_active_goals(user_id, supabase)
        _try_add("goals", goals_text)
    else:
        layers.append(LayerResult("goals", False, 0, "no supabase client"))

    # Layer 5: Memory retrieval (Phase 3, simplified after the structured
    # pre-filter was removed). A word-overlap pre-filter (find_structured_
    # candidates in discovery.py) was tried and removed: "Where do I work?"
    # matched the location file over employment, because it shares the word
    # "where" with location's summary ("Where Clifford is currently based")
    # while sharing zero words with employment's ("employers", "roles") --
    # confirmed directly, not a hypothetical. Pre-loading a file and labeling
    # it AUTHORITATIVE created a false-authority risk worse than not
    # pre-loading anything. The context builder now only supplies semantic
    # hints (Mem0 + the index); the agent itself decides which structured
    # file to read via read_memory_file_tool, matching the explicit principle
    # that the agent reasons about relevance, not a pre-filter.
    from backend.memory.memory_files import get_memory_index
    from backend.memory.mem0_client import recall as mem0_recall

    # 5a: Mem0 semantic search -- the one retrieval call in this layer
    mem0_text = await mem0_recall(current_message, user_id=user_id, top_k=5)
    if mem0_text:
        _try_add("memory", f"## SUPPORTING SEMANTIC MEMORY\n{mem0_text}")
    else:
        layers.append(LayerResult("memory", False, 0, "no relevant memories found"))

    # 5b: Memory index -- unchanged from Phase 2, always injected. The agent
    # reads this, identifies which file (if any) is relevant, and calls
    # read_memory_file_tool itself -- no file content is pre-loaded here.
    memory_index = get_memory_index(user_id)
    _try_add("memory_index", memory_index)

    # Layer 6: Conversation summary — conversation_summaries table does not
    # exist yet (Phase 3 creates it). Returns None until then; never create
    # the table or generate a summary here.
    if supabase:
        summary = _get_conversation_summary(conversation_id, supabase)
        if summary:
            _try_add("summary", summary)
        else:
            layers.append(LayerResult("summary", False, 0, "table doesn't exist yet"))
    else:
        layers.append(LayerResult("summary", False, 0, "no supabase client"))

    assembled = "\n\n".join(sections)
    result = ContextResult(
        text=assembled,
        total_tokens=_count_tokens(assembled),
        layers=layers,
    )
    print(f"[context] {result.log_summary()}")
    return result


def _get_user_profile(user_id: str, supabase) -> Optional[str]:
    """
    Fetch user profile from the real `users` table columns:
    display_name, timezone, home_address, home_lat/lng, work_address,
    work_lat/lng. (morning_nudge_time, named_locations, created_at,
    updated_at exist but aren't relevant to the system prompt.)
    """
    try:
        res = supabase.table("users")\
            .select("display_name, timezone, home_lat, home_lng, home_address, work_lat, work_lng, work_address")\
            .eq("id", user_id)\
            .maybe_single()\
            .execute()
        profile = res.data if res and res.data else None
        if not profile:
            return None

        lines = []
        name = profile.get("display_name")
        if name:
            lines.append(f"USER'S NAME: {name} — address them by this name.")
        tz = profile.get("timezone")
        if tz:
            lines.append(f"Timezone: {tz}")
        home_lat, home_lng = profile.get("home_lat"), profile.get("home_lng")
        if home_lat and home_lng:
            lines.append(f"Home: {profile.get('home_address') or 'Home'} (coordinates: {home_lat}, {home_lng})")
        work_lat, work_lng = profile.get("work_lat"), profile.get("work_lng")
        if work_lat and work_lng:
            lines.append(f"Work: {profile.get('work_address') or 'Work'} (coordinates: {work_lat}, {work_lng})")
        return "\n".join(lines) if lines else None
    except Exception as e:
        print(f"[context] profile fetch failed (non-fatal): {e}")
        return None


def _get_active_goals(user_id: str, supabase) -> Optional[str]:
    """
    Fetch active goals from the real `goals` table columns:
    title, status, urgency. Returns None if there are no active goals.
    """
    try:
        res = supabase.table("goals")\
            .select("title, urgency")\
            .eq("user_id", user_id)\
            .eq("status", "active")\
            .execute()
        rows = res.data or []
        if not rows:
            return None
        lines = ["## Active goals"]
        for g in rows:
            lines.append(f"- {g['title']} (urgency: {g.get('urgency', 'medium')})")
        return "\n".join(lines)
    except Exception as e:
        print(f"[context] goals fetch failed (non-fatal): {e}")
        return None


def _get_conversation_summary(conversation_id: str, supabase) -> Optional[str]:
    """
    Fetch summary from a dedicated conversation_summaries table. That table
    does not exist in the current schema (Phase 3 creates it) — any query
    error (including "table does not exist") is swallowed and this layer
    is reported as excluded, never as a crash.
    """
    try:
        result = supabase.table("conversation_summaries")\
            .select("summary")\
            .eq("conversation_id", conversation_id)\
            .maybe_single()\
            .execute()
        return result.data["summary"] if result and result.data else None
    except Exception:
        return None  # table absent or query error — silent, non-fatal


def _format_world_state(ws: dict) -> str:
    t = ws.get("temporal", {})
    l = ws.get("location", {})
    e = ws.get("environment", {}).get("weather", {})
    lines = ["## Current Context"]
    if t.get("time_of_day") or t.get("timestamp"):
        lines.append(
            f"Time: {t.get('time_of_day', '')} · {str(t.get('timestamp', ''))[:16]}"
        )
    if l.get("city"):
        lines.append(f"Location: {l.get('district', '')}, {l.get('city', '')}")
    if e.get("description"):
        lines.append(f"Weather: {e.get('description', '')}, {e.get('temp_c', '')}°C")
    return "\n".join(lines) if len(lines) > 1 else ""
