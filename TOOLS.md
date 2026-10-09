# JARVIS Tools — Architecture, Inventory, and How to Add More

This document is for whoever (human or AI coding agent) adds new tools to
JARVIS. Read the whole thing before writing code — the dual-path
requirement (every tool must work in **both** text and voice) is the part
most likely to be gotten wrong, and section 3 exists specifically to stop
that mistake before it ships.

**Golden rule: additive and safe.** Never remove or modify an existing
tool's behavior to add a new one. Never change `backend/agent.py`'s
`BASE_SYSTEM_PROMPT` wording for existing tools. Never touch Mem0,
`memory_files`, or `relationship_notes` schemas to make a new tool "fit."
If a new tool needs new state, add a new table/column — don't repurpose
an existing one.

---

## 1. The one-source-of-truth architecture

JARVIS has exactly **one list of tools**, defined in `backend/agent.py`:

```python
ALL_TOOLS = [
    get_world_state,
    send_nudge,
    get_goals,
    manage_goal,
    web_search,
    get_exchange_rate,
    calculate,
    create_timer,
    hybrid_search_notes_tool,
    add_person,
    add_note_for_person,
    update_person_tool,
    find_nearby_places,
    get_route_and_traffic,
    check_traffic_to_saved_location,
    search_place_by_name,
    set_named_location,
    create_reminder,
    search_my_memory,
    save_to_memory,
    read_memory_file_tool,
    update_memory_file_tool,
    append_to_memory_file_tool,
    create_memory_file_tool,
]
```

- **Text agent** (`backend/agent.py`'s `build_graph()`) uses `ALL_TOOLS` directly —
  these are LangChain `@tool` objects, invoked natively by LangGraph's
  `create_react_agent`.
- **Voice agent** (`backend/voice/tool_adapter.py`) imports the *same*
  `ALL_TOOLS` list from `backend/agent.py` (`from backend.agent import ALL_TOOLS`)
  and wraps each one as a LiveKit `@function_tool`. It does **not** keep
  its own separate tool list anymore — this was fixed because it used to,
  and tools occasionally went missing from one path but not the other.

**Consequence: adding a tool to `ALL_TOOLS` in `agent.py` makes it available
in voice automatically.** You do not need to touch `tool_adapter.py` to add
a new tool, unless that tool needs voice-specific restriction (see §3.3).

### Why two different calling conventions exist at all

LangChain (text, via LangGraph) and the LiveKit Agents SDK (voice) have
different tool-calling conventions:

| | Text (LangChain `@tool`) | Voice (LiveKit `@function_tool`) |
|---|---|---|
| Definition | `@tool` decorator, typed function signature | Plain async function, `raw_schema=` dict |
| Call shape | Individual typed kwargs | Single `raw_arguments: dict` positional arg |
| Schema source | Auto-derived from type hints via Pydantic | Must be hand-built from the LangChain tool's own `args_schema.model_json_schema()` |

`tool_adapter.py`'s `_build_voice_tool()` does this translation automatically
for every tool in `ALL_TOOLS` — you never write LiveKit-specific tool code
by hand. **This is the mechanism that makes "every tool accessible by voice
and text" true without double the work.**

---

## 2. Identity and security — read before adding any tool that touches user data

Several tools take `user_id` as a parameter (e.g. `get_world_state`,
`add_person`, `create_reminder`). This value must **never** be trusted from
the LLM.

- **Text path**: `user_id` is injected into the system prompt as a known
  value ("USER_ID: <uuid>, always use this exact value"). This is an
  instruction, not an enforced guarantee — a known gap, intentionally not
  fixed yet (see §5).
- **Voice path**: `tool_adapter.py`'s `_build_voice_tool()` strips `user_id`
  entirely from what the LLM sees in the tool's schema, and overwrites
  whatever the LLM supplies with the real authenticated `user_id` captured
  server-side from the LiveKit room token. This is enforced, not just
  instructed.

**If your new tool takes `user_id`**: no extra work needed — `tool_adapter.py`
detects the `user_id` field on any tool's `args_schema` automatically and
applies the same override. You get this for free by adding the tool to
`ALL_TOOLS`.

---

## 3. How to add a new tool — exact checklist

Follow these steps in order. Each step names the exact file.

### 3.1 Define the tool

Pick the right file under `backend/tools/` by category (or create a new
one if it's a genuinely new category):

- `world_tools.py` — ambient state, nudges, timers, named locations
- `maps_tools.py` — TomTom-backed location/routing
- `goal_tools.py` — goals
- `search_tools.py` — web search, currency, calculator
- `relationship_tools.py` — people/notes/reminders
- `backend/memory/tools.py` — Mem0 semantic memory
- `backend/memory/file_tools.py` — structured memory files

Write it as a LangChain `@tool`:

```python
from langchain_core.tools import tool

@tool
async def your_new_tool(user_id: str, some_arg: str) -> dict:
    """
    One-line summary (this becomes the tool's description everywhere,
    including the auto-generated system-prompt tool list — see §4).

    CALL THIS when the user:
    - "example phrase that should trigger this tool"
    - "another example phrase"

    Explain any non-obvious argument here.
    """
    ...
    return {"status": "...", ...}
```

Rules:
- Always `async def`, even if the body has no real await (consistency
  with the rest of the codebase; LangGraph and LiveKit both call tools
  as coroutines).
- Return a `dict` or `list[dict]`, not a bare string, unless the tool is
  conceptually just a string answer (like `web_search`, `calculate`).
- The docstring's **first line** is what appears in the system prompt's
  auto-generated tool list (§4) — make it a clear, specific one-liner.
- If the tool touches a specific user's data, take `user_id: str` as the
  first parameter — this is what triggers the automatic identity
  enforcement in voice (§2).
- Wrap all DB/API calls in `try/except`, return `{"status": "error",
  "detail": str(e)}` rather than raising — an uncaught exception in a
  tool call surfaces as a dead end to the user in both text and voice.

### 3.2 Wire it into the text agent

In `backend/agent.py`:
1. Add the import at the top (alongside the existing tool imports).
2. Add the tool to the `ALL_TOOLS` list.

That's it for text. **Do not** add it to any other list — `ALL_TOOLS` is
the only list that matters.

### 3.3 Wire it into voice (only if it needs special handling)

Because voice imports `ALL_TOOLS` directly from `agent.py`, **step 3.2
alone is enough to make the tool voice-accessible.** Only come back to
`backend/voice/tool_adapter.py` if your tool needs a voice-specific
restriction — e.g. it's destructive and has no undo (see
`_is_destructive_goal_action()` for the existing pattern, which blocks
`manage_goal`'s delete action in voice only). If so, add a similar guard
inside `_build_voice_tool()`'s `handler()`.

### 3.4 Add a system-prompt usage rule (if the tool needs one)

Most tools work fine with just their docstring's "CALL THIS when..."
section (the LLM reads tool descriptions directly). Only add an explicit
rule to `BASE_SYSTEM_PROMPT` in `backend/agent.py` if:
- The tool must ALWAYS be called before answering certain questions
  (see the "Relationship memory — CRITICAL RULES" section as a pattern)
- There's a specific sequencing requirement with another tool
- There's a common mistake the LLM needs to be steered away from

Keep additions in their own clearly-labeled `##` section, same pattern as
the existing "RENAMING/CORRECTING A PERSON" section. Do not edit existing
sections.

### 3.5 Test both paths

Minimum bar before calling a new tool done:

```python
# Direct tool test (fast, no LLM involved)
from backend.tools.your_module import your_new_tool
result = await your_new_tool.ainvoke({"user_id": "...", "some_arg": "..."})
print(result)
```

```python
# Through the real agent graph (confirms the LLM actually calls it
# correctly, with the right args, at the right time)
from backend.agent import build_graph, BASE_SYSTEM_PROMPT
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

graph = build_graph(checkpointer=MemorySaver())
result = await graph.ainvoke(
    {"messages": [HumanMessage(content="a phrase that should trigger your tool")],
     "system_prompt": f"USER_ID: ...\n\n{BASE_SYSTEM_PROMPT}"},
    config={"configurable": {"thread_id": "test"}},
)
```

For voice: `from backend.voice.tool_adapter import get_voice_tools` and
confirm your tool appears in the returned list (`len()` should go up by
exactly one). Full live voice testing requires a real LiveKit session —
not always practical per-tool, but the above confirms the wiring is
correct.

**Always clean up test data you create** (delete test rows from Supabase)
— several real bugs in this codebase's history came from stale test rows
left in `people`, `memory_files`, `nudge_history`, etc.

---

## 4. The system prompt always knows every tool — how, and why it can't drift

`backend/agent.py` has a function `render_tool_list()` that iterates
`ALL_TOOLS` and extracts each tool's `name` and the first line of its
docstring. This rendered list is appended to `BASE_SYSTEM_PROMPT` under an
"## Available tools" heading, generated once at import time:

```python
BASE_SYSTEM_PROMPT = _BASE_SYSTEM_PROMPT_TEMPLATE.replace(
    "__TOOL_LIST_PLACEHOLDER__", render_tool_list()
)
```

This means: **you cannot add a tool to `ALL_TOOLS` without it also
appearing in the system prompt's tool list.** There is no separate place
that needs manual updating, and no way for this to go stale as tools are
added — it is regenerated from the actual tool objects every time the
module loads. This same `BASE_SYSTEM_PROMPT` is what both the text path
(`backend/context/builder.py`) and voice path
(`backend/voice/context.py`'s `build_voice_system_prompt()`) start from, so
both interfaces' LLMs always see the same accurate list.

Do not hand-write a tool list anywhere else in the codebase. If you're
tempted to, you're duplicating something `render_tool_list()` already does
correctly.

---

## 5. Known, intentional gaps (do not "fix" these as a side effect of adding a tool)

- **Text-path `user_id` is instruction-enforced, not server-enforced.**
  Flagged, not fixed, because fixing it mid-feature-work risked
  destabilizing working systems. If you're asked to fix this specifically,
  treat it as its own task, not a drive-by change while adding a tool.
- **Mem0 is ADD-only** (no native update/delete of facts). Don't try to
  make a new tool "update" a Mem0 fact directly — route durable-state
  changes through `memory_files` (`update_memory_file_tool`) instead, and
  person-specific facts through `relationship_notes`
  (`add_note_for_person`/`update_person_tool`).
- **No automatic memory-conflict resolution.** An earlier attempt at this
  (LLM-judged fact superseding) caused real data loss and was fully
  disabled. Do not re-attempt automatic retiring/deleting of memories as
  part of a new tool.
- **TomTom, Tavily, Deepgram, LiveKit all require API keys in `.env`.** A
  tool that silently returns empty/error results is more likely a missing
  or wrong key than a code bug — check `.env` first.

---

## 6. Tools JARVIS does not have yet (ideas, not commitments)

These are suggestions for what would make JARVIS more useful, each scoped
to fit the existing architecture without breaking anything. None of these
are required — pick based on what's actually useful to Clifford day to
day.

### Calendar integration (real, not stubbed)
`backend/world_state.py`'s `fetch_calendar()` is currently a stub returning
empty structure (explicitly marked "Phase 2" in a comment, never built).
A real Google Calendar read-only integration (OAuth, list today's events)
would let `get_world_state` and proactive nudges actually reason about
meeting load, which several existing fields (`meeting_fatigue_score`,
`in_meeting_now`) already expect but never receive real data for.

### Email tools (read-only first)
A `search_my_email` / `summarize_recent_emails` tool (Gmail API,
read-only scope) would let JARVIS answer "did I get a reply from X" or
"summarize my unread emails" — high-value, and a natural extension of
"personal AI operating system."

### Note/document tools
A `save_document_snippet` / `search_documents` pair, backed by a new table
(not `memory_files` — that's for structured durable facts, not arbitrary
documents) with pgvector embeddings, for pasting in longer text (meeting
notes, articles) and later searching it.

### Delete/archive tools (careful, additive-safe design required)
Currently `manage_goal` supports delete but voice blocks it, and there's
no delete path at all for memory files or relationship notes. If you add
one, make it two-step (soft-delete/archive flag first, hard-delete only
via a separate explicit confirmation path) — given this project's history
with accidental data loss, any delete-capable tool needs more scrutiny
than an additive one.

### Habit/routine tracking
A `log_habit` / `get_habit_streak` pair (new small table) — "log that I
worked out today," "what's my streak." Fits the proactive-assistant
positioning well and is low-risk (purely additive, new table, no
interaction with existing schemas).

### Finance tracking
A `log_expense` / `get_spending_summary` pair. Natural fit given
`get_exchange_rate` already exists. New table, additive, no schema risk.

### Multi-person meeting notes (after diarization groundwork)
`backend/livekit_agent.py` already logs `speaker_id` from Deepgram
diarization (currently log-only, no behavior change — see the comment
above `enable_diarization=True`). A future tool could let JARVIS
summarize a multi-speaker voice session with notes attributed per
speaker_id, without yet solving "who is speaker 2" identity mapping —
that's a separate, harder problem.

---

## 7. What NOT to do

- Do not introduce a second tool-list anywhere. `ALL_TOOLS` in
  `backend/agent.py` is the only one.
- Do not make `tool_adapter.py` maintain its own tool list again — it
  imports `ALL_TOOLS` from `agent.py` on purpose.
- Do not change existing tool docstrings' "CALL THIS when" trigger phrases
  without testing that the existing trigger phrases still work — the LLM's
  tool-selection quality depends on these being accurate.
- Do not add a new top-level system prompt section without a clear `##`
  heading, and do not edit existing sections to "make room."
- Do not touch Mem0's lifecycle, `memory_files`' schema, or
  `relationship_notes`' schema to make a new tool fit — add new tables
  instead.
- Do not remove the TOMTOM/TAVILY/DEEPGRAM "missing key" error-return
  pattern in existing tools (returning `{"error": "...not configured"}`
  rather than raising) — this is what lets the app run gracefully with a
  subset of integrations configured.
