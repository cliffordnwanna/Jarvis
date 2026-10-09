"""
Adapts existing LangChain tools for use in the LiveKit Agents SDK voice
agent. Imports the SAME underlying tool objects as backend/agent.py -- no
duplication, no reimplementation. Only the calling convention differs:
LangGraph invokes LangChain @tool objects directly; the LiveKit Agents SDK
wants plain async functions wrapped with @function_tool.

Identity safety: several of these LangChain tools declare `user_id` as a
field in their own args_schema. For voice, every wrapped tool here
OVERRIDES whatever user_id argument the LLM supplies with the real
authenticated user_id captured from the LiveKit room's token at session
start -- the LLM never controls which user's data a tool call touches.

Text now has an equivalent (but differently-mechanized) guarantee: the
same tools' user_id parameters are annotated
Annotated[str, InjectedState("user_id")] (backend/agent.py's JarvisState
carries user_id, set from main.py's authenticated get_current_user()), so
LangGraph's ToolNode fills the value from graph state rather than the
LLM's tool-call arguments -- confirmed via a live test where the LLM's
tool call had args={} and the tool still received the real injected
value. Both paths now enforce this server-side; neither trusts an
LLM-supplied user_id. (Fixed during the UUID/isolation audit -- previously
only voice had this guarantee.)
"""
from __future__ import annotations
import logging
from typing import Callable

from livekit.agents.llm import function_tool

logger = logging.getLogger(__name__)

# Single source of truth: the exact same list object backend/agent.py's
# build_graph() uses. Importing it directly (rather than re-listing every
# tool here) means a tool added to ALL_TOOLS in agent.py is automatically
# available in voice too -- no second place to remember to update, and no
# way for the two tool sets to silently drift apart. See TOOLS.md.
from backend.agent import ALL_TOOLS


def _is_destructive_goal_action(tool_name: str, args: dict) -> bool:
    """
    The one write excluded from voice: manage_goal's delete action. A
    delete has no undo and no visual confirmation step in voice-only
    interaction, unlike every other tool here (additive, or in-place
    updates that preserve history in text, like update_memory_file_tool).
    """
    return tool_name == "manage_goal" and args.get("action") == "delete"


def _build_voice_tool(tool, authenticated_user_id: str) -> Callable:
    """
    Wrap one LangChain tool as a LiveKit @function_tool. The wrapper's own
    signature is built from the tool's real args_schema (Pydantic v2
    model_json_schema()), minus user_id -- removed from what the LLM sees
    entirely, since user_id is never a value the model should be choosing.
    The real, authenticated user_id is injected server-side on every call.
    """
    has_user_id_field = bool(
        tool.args_schema and "user_id" in tool.args_schema.model_fields
    )

    # Confirmed via direct source inspection (livekit.agents.beta.toolsets
    # .tool_search's real _handle_search method) that a @function_tool(
    # raw_schema=...) handler takes ONE positional dict argument
    # (raw_arguments), not **kwargs -- an earlier draft of this file
    # assumed **kwargs, which is wrong for this calling convention.
    async def handler(raw_arguments: dict) -> str:
        kwargs = dict(raw_arguments)
        if has_user_id_field:
            kwargs["user_id"] = authenticated_user_id

        if _is_destructive_goal_action(tool.name, kwargs):
            return (
                "I can't delete goals through voice yet -- "
                "please do that from the app for now."
            )

        try:
            return await tool.ainvoke(kwargs)
        except Exception as e:
            logger.error(f"[voice tool] {tool.name} failed with args {kwargs}: {e}", exc_info=True)
            return f"Tool error: {e}"

    handler.__name__ = tool.name
    handler.__doc__ = tool.description

    # Build the raw JSON schema the LLM is actually shown, with user_id
    # stripped -- the LLM is never given the option to supply it.
    if tool.args_schema:
        full_schema = tool.args_schema.model_json_schema()
        properties = {k: v for k, v in full_schema.get("properties", {}).items() if k != "user_id"}
        required = [r for r in full_schema.get("required", []) if r != "user_id"]
    else:
        properties, required = {}, []

    raw_schema = {
        "name": tool.name,
        "description": tool.description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }

    return function_tool(handler, raw_schema=raw_schema)


def get_voice_tools(authenticated_user_id: str) -> list:
    """
    Return every tool as a LiveKit function_tool, bound to one session's
    authenticated user_id. Called once per voice session (not shared
    across sessions/users), so each session's tools are scoped to exactly
    the user who authenticated for that LiveKit room token.
    """
    return [_build_voice_tool(t, authenticated_user_id) for t in ALL_TOOLS]
