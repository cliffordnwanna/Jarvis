from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.db.postgres import get_supabase
from livekit.api import AccessToken, VideoGrants
import json
import os
import uuid

router = APIRouter()


@router.get("/token")
async def get_livekit_token(
    conversation_id: str | None = None,
    user_id: str = Depends(get_current_user),
):
    """
    Generate a LiveKit room token for the authenticated user.
    Room name is jarvis-{user_id} — unique per user (pre-existing convention,
    unchanged here; LIVEKIT_API_SECRET never leaves the server and token
    minting is auth-gated, so the room name itself is not a secret).

    conversation_id, when supplied by the frontend (its existing
    jarvis_thread_id from Phase 0), is carried in the room metadata so the
    voice worker can persist turns to the SAME conversations/messages rows
    text chat uses -- voice does not get a separate conversation. A
    reconnect that sends the same conversation_id continues that
    conversation rather than starting a new one (per explicit requirement:
    a dropped WebRTC connection is not a new JARVIS conversation).
    When omitted, a fresh conversation_id is generated.
    """
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not livekit_api_key or not livekit_api_secret:
        raise HTTPException(500, "LiveKit not configured")

    db = get_supabase()
    profile = db.table("users").select("display_name").eq("id", user_id).maybe_single().execute()
    user_name = (profile.data or {}).get("display_name") or user_id[:8]

    room_name = f"jarvis-{user_id}"
    resolved_conversation_id = conversation_id or str(uuid.uuid4())

    token = (
        AccessToken(livekit_api_key, livekit_api_secret)
        .with_identity(user_id)
        .with_name(user_name)
        .with_metadata(json.dumps({
            "user_id": user_id,
            "conversation_id": resolved_conversation_id,
        }))
        .with_grants(VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
        .to_jwt()
    )

    return {
        "token": token,
        "room": room_name,
        "url": os.getenv("LIVEKIT_URL"),
        "conversation_id": resolved_conversation_id,
    }
