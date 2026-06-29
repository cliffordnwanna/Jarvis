from langchain_core.tools import tool
from backend.db.postgres import get_supabase
from datetime import datetime, timezone


@tool
async def get_goals(user_id: str) -> list:
    """
    Retrieve all active goals for the user from the database.

    ALWAYS CALL THIS before answering any question about:
    - "What are my goals?"
    - "What should I focus on?"
    - "What am I working towards?"
    - "What tasks do I have?"
    - "How am I doing on my goals?"

    Never answer goal questions from memory — always fetch fresh from DB.
    Returns list of goals with title, urgency (low/medium/high), and last_touched_at.
    """
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
    Create, complete, or update a goal.

    CALL THIS when user says:
    - "Add X as a goal" / "I want to achieve X" → action="create"
    - "I completed X" / "Mark X as done"       → action="complete"
    - "I worked on X today" / "Progress on X"  → action="touch"

    action options: create, complete, touch
    urgency options: low, medium, high
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
