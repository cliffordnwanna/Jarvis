from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from backend.auth import get_current_user
from backend.db.postgres import get_supabase

router = APIRouter()


class GoalCreate(BaseModel):
    title: str
    urgency: str = "medium"


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    urgency: Optional[str] = None


@router.get("")
async def list_goals(user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("goals").select("*").eq("user_id", user_id).eq("status", "active").execute()
    return res.data or []


@router.post("")
async def create_goal(goal: GoalCreate, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("goals").insert({
        "user_id": user_id,
        "title": goal.title,
        "urgency": goal.urgency,
    }).execute()
    return res.data[0] if res.data else {}


@router.patch("/{goal_id}")
async def update_goal(goal_id: str, updates: GoalUpdate, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    data = {k: v for k, v in updates.model_dump().items() if v is not None}
    res = db.table("goals").update(data).eq("id", goal_id).eq("user_id", user_id).execute()
    return res.data[0] if res.data else {}


@router.delete("/{goal_id}")
async def archive_goal(goal_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    db.table("goals").update({"status": "completed"}).eq("id", goal_id).eq("user_id", user_id).execute()
    return {"status": "archived"}


@router.post("/{goal_id}/touch")
async def touch_goal(goal_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    db.table("goals").update({
        "last_touched_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", goal_id).eq("user_id", user_id).execute()
    return {"status": "touched"}
