"""
Conversation identity and persistence for voice sessions.

Reuses the existing conversations/messages tables exactly as text does --
no new schema, no parallel persistence mechanism. A voice session's
conversation_id is the LiveKit room name (stripped of the "jarvis-" prefix
is the user_id; the conversation_id itself is a separate value passed
through the room metadata / token, matching how main.py's /agent endpoint
treats thread_id as the conversations.id primary key).

Per explicit correction: a reconnect is not necessarily a new conversation.
get_or_create_voice_conversation() only creates a new row when the given
conversation_id has no existing row -- the caller decides, from its own
session state, whether a reconnect should reuse the prior conversation_id
or start a new one.
"""
from __future__ import annotations
from backend.db.postgres import get_supabase


async def get_or_create_voice_conversation(conversation_id: str, user_id: str) -> bool:
    """
    Ensure a conversations row exists for conversation_id. Mirrors
    backend/main.py's get_or_create_conversation() exactly -- same table,
    same insert shape -- so a voice conversation is indistinguishable from
    a text one in the conversations table and appears in the sidebar.

    Returns True if this call created the row (first turn of this voice
    conversation), matching the text endpoint's is_first_message signal.
    """
    db = get_supabase()
    try:
        existing = db.table("conversations").select("id").eq("id", conversation_id).maybe_single().execute()
        if existing and existing.data:
            return False
    except Exception as e:
        print(f"[voice conversation] lookup error: {e}")

    try:
        db.table("conversations").insert({
            "id": conversation_id,
            "user_id": user_id,
            "title": "Voice conversation",
        }).execute()
        return True
    except Exception as e:
        print(f"[voice conversation] create error (non-fatal): {e}")
        return False


async def persist_voice_turn(conversation_id: str, user_id: str, role: str, content: str) -> None:
    """
    Write one voice turn to the messages table -- the same table, same
    shape, as backend/main.py's persist_message(). A voice turn and a text
    turn are rows in the same table; the chat sidebar renders both the
    same way with no special-casing.
    """
    if not content or not content.strip():
        return
    try:
        db = get_supabase()
        db.table("messages").insert({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
        }).execute()
    except Exception as e:
        print(f"[voice conversation] persist error (non-fatal): {e}")
