from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.db.postgres import get_supabase
from livekit.api import AccessToken, VideoGrants
import os

router = APIRouter()


@router.get("/token")
async def get_livekit_token(user_id: str = Depends(get_current_user)):
    """
    Generate a LiveKit room token for the authenticated user.
    Room name is jarvis-{user_id} — unique per user.
    """
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not livekit_api_key or not livekit_api_secret:
        raise HTTPException(500, "LiveKit not configured")

    db = get_supabase()
    profile = db.table("users").select("display_name").eq("id", user_id).maybe_single().execute()
    user_name = (profile.data or {}).get("display_name") or user_id[:8]

    room_name = f"jarvis-{user_id}"

    token = (
        AccessToken(livekit_api_key, livekit_api_secret)
        .with_identity(user_id)
        .with_name(user_name)
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
    }
