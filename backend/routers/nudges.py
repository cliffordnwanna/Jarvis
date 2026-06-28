from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from backend.auth import get_current_user
from backend.db.postgres import get_supabase

router = APIRouter()


@router.get("")
async def list_nudges(limit: int = 20, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("nudge_history") \
        .select("*") \
        .eq("user_id", user_id) \
        .is_("dismissed_at", "null") \
        .order("delivered_at", desc=True) \
        .limit(limit) \
        .execute()
    return res.data or []


@router.delete("/{nudge_id}")
async def dismiss_nudge(nudge_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    db.table("nudge_history") \
        .update({"dismissed_at": datetime.now(timezone.utc).isoformat()}) \
        .eq("id", nudge_id) \
        .eq("user_id", user_id) \
        .execute()
    return {"status": "dismissed", "id": nudge_id}


@router.delete("")
async def dismiss_all(user_id: str = Depends(get_current_user)):
    db = get_supabase()
    db.table("nudge_history") \
        .update({"dismissed_at": datetime.now(timezone.utc).isoformat()}) \
        .eq("user_id", user_id) \
        .is_("dismissed_at", "null") \
        .execute()
    return {"status": "all dismissed"}


@router.post("/{nudge_id}/action")
async def action_nudge(nudge_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    db.table("nudge_history") \
        .update({"actioned": True}) \
        .eq("id", nudge_id) \
        .eq("user_id", user_id) \
        .execute()
    return {"status": "actioned"}
