"""
Builds the system prompt for voice interactions.

Reuses BASE_SYSTEM_PROMPT and the real memory/relationship rules from
backend/agent.py rather than recreating them -- per explicit instruction,
voice must not get a separate interpretation of the memory rules.

Does not call build_context() from backend/context/builder.py directly:
that function is written for the request-scoped text /agent endpoint (it
takes conversation_id, world_state, profile_text, world_state_text as
pre-formatted strings assembled by main.py's per-request logic) and would
need that same request-shaped data reconstructed here for no benefit --
the memory CONTENT it assembles (Mem0 recall + memory index) is pulled in
directly below instead, via the same underlying functions build_context()
itself calls, so the memory rules and content are identical either way.
This is documented here as a deliberate difference, not a silent gap,
per Correction 9.
"""
from __future__ import annotations

from backend.agent import BASE_SYSTEM_PROMPT
from backend.memory.mem0_client import recall as mem0_recall
from backend.memory.memory_files import get_memory_index
from backend.db.postgres import get_supabase


async def build_voice_system_prompt(user_id: str, current_message: str = "") -> str:
    """
    Assemble the system prompt for voice. Same base instructions and memory
    rules as text, plus a voice-specific response-style addendum appended
    (never replacing) the base prompt.
    """
    prompt = f"USER ID (use this exact UUID for ALL tool calls that need user_id): {user_id}\n\n"
    prompt += BASE_SYSTEM_PROMPT

    # Same memory content as text's Layer 5: Mem0 semantic recall + the
    # structured memory file index. The agent decides whether to call
    # read_memory_file_tool from the index, exactly as in text.
    try:
        memory_index = get_memory_index(user_id)
    except Exception as e:
        print(f"[voice context] memory index error (non-fatal): {e}")
        memory_index = ""
    if memory_index:
        prompt += f"\n\n{memory_index}"

    if current_message:
        try:
            mem0_text = await mem0_recall(current_message, user_id=user_id)
        except Exception as e:
            print(f"[voice context] mem0 recall error (non-fatal): {e}")
            mem0_text = ""
        if mem0_text:
            prompt += f"\n\n## SUPPORTING SEMANTIC MEMORY\n{mem0_text}"

    # Voice-specific style guidance -- appended, not replacing base prompt.
    prompt += """

## Voice response style
You are responding via voice. Adjust accordingly:
- Be concise. Long responses are hard to listen to.
- Never read markdown. No headers, bullets, or code blocks aloud.
- Instead of "## Employment:" say "You work at..."
- Natural spoken language only.
- If you need to use a memory tool, do so silently and speak the result.
"""
    return prompt
