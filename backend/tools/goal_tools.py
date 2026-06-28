from langchain_core.tools import tool
from backend.db.postgres import get_supabase
from datetime import datetime, timezone


@tool
async def get_goals(user_id: str) -> list:
    """Get all active goals for the user."""
    db = get_supabase()
    res = db.table("goals").select("*").eq("user_id", user_id).eq("status", "active").execute()
    return res.data or []


@tool
async def manage_goal(
    user_id: str,
    action: str,
    title: str = None,
    goal_id: str = None,
    urgency: str = "medium",
) -> dict:
    """
    Create, complete, or touch a goal.
    Actions:
      - create: requires title
      - complete: requires goal_id
      - touch: requires goal_id (marks as worked on today)
    """
    db = get_supabase()
    if action == "create" and title:
        res = db.table("goals").insert({
            "user_id": user_id,
            "title": title,
            "urgency": urgency,
        }).execute()
        return {"status": "created", "goal": res.data[0] if res.data else {}}
    elif action == "complete" and goal_id:
        db.table("goals").update({"status": "completed"}).eq("id", goal_id).execute()
        return {"status": "completed"}
    elif action == "touch" and goal_id:
        db.table("goals").update({
            "last_touched_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", goal_id).execute()
        return {"status": "touched"}
    return {"error": "Invalid action or missing parameters. Actions: create, complete, touch."}
