from backend.db.postgres import get_supabase
from datetime import datetime, timezone


async def cache_set(user_id: str, value: dict, ttl_seconds: int = 300):
    db = get_supabase()
    db.table("world_state").upsert({
        "user_id": user_id,
        "state": value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id").execute()


async def cache_get(user_id: str, ttl_seconds: int = 300) -> dict | None:
    db = get_supabase()
    try:
        res = db.table("world_state")\
            .select("state, updated_at")\
            .eq("user_id", user_id)\
            .maybe_single()\
            .execute()
        if not res or not res.data:
            return None
        updated = datetime.fromisoformat(
            res.data["updated_at"].replace("Z", "+00:00")
        )
        if (datetime.now(timezone.utc) - updated).seconds > ttl_seconds:
            return None
        return res.data["state"]
    except Exception:
        return None


async def cache_delete(user_id: str):
    db = get_supabase()
    db.table("world_state").delete().eq("user_id", user_id).execute()
