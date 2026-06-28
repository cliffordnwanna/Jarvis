from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from backend.auth import get_current_user
from backend.db.postgres import get_supabase

router = APIRouter()


class ReminderCreate(BaseModel):
    title: str
    scheduled_at: str
    person_id: Optional[str] = None
    event_type: str = "check_in"
    context: dict = {}


@router.post("")
async def create_reminder(reminder: ReminderCreate, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    data = {
        "user_id": user_id,
        "title": reminder.title,
        "scheduled_at": reminder.scheduled_at,
        "event_type": reminder.event_type,
        "nudge_sent": False,
        "context": reminder.context,
        "person_id": reminder.person_id,
    }
    res = db.table("relationship_events").insert(data).execute()
    return res.data[0] if res.data else {}


@router.get("")
async def list_reminders(user_id: str = Depends(get_current_user)):
    db = get_supabase()
    now = datetime.now(timezone.utc)
    res = db.table("relationship_events")\
        .select("*, people(name)")\
        .eq("user_id", user_id)\
        .is_("completed_at", "null")\
        .gte("scheduled_at", now.isoformat())\
        .order("scheduled_at")\
        .execute()
    return res.data or []


@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    db.table("relationship_events")\
        .update({"completed_at": datetime.now(timezone.utc).isoformat()})\
        .eq("id", reminder_id)\
        .eq("user_id", user_id)\
        .execute()
    return {"status": "deleted"}
