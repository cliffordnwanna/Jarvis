from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from backend.auth import get_current_user
from backend.db.postgres import get_supabase

router = APIRouter()


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    timezone: Optional[str] = None
    morning_nudge_time: Optional[str] = None
    home_lat: Optional[float] = None
    home_lng: Optional[float] = None


@router.patch("/profile")
async def update_profile(
    updates: ProfileUpdate,
    user_id: str = Depends(get_current_user),
):
    db = get_supabase()
    data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not data:
        return {"status": "nothing to update"}

    db.table("users").update(data).eq("id", user_id).execute()

    # Clear profile cache so next agent call picks up new name
    try:
        import backend.main as _main
        _main._user_profile_cache.pop(user_id, None)
    except Exception:
        pass

    return {"status": "updated", "fields": list(data.keys())}


@router.get("/profile")
async def get_profile(user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("users")\
        .select("display_name, timezone, morning_nudge_time, home_lat, home_lng")\
        .eq("id", user_id)\
        .maybe_single()\
        .execute()
    return res.data or {}
