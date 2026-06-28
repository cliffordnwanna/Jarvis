from fastapi import APIRouter, Depends
from backend.auth import get_current_user
from backend.db.postgres import get_supabase

router = APIRouter()


@router.get("/conversations")
async def list_conversations(limit: int = 20, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("conversations") \
        .select("id, title, created_at, last_message_at") \
        .eq("user_id", user_id) \
        .order("last_message_at", desc=True) \
        .limit(limit) \
        .execute()
    return res.data or []


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    conv = db.table("conversations") \
        .select("*") \
        .eq("id", conversation_id) \
        .eq("user_id", user_id) \
        .single() \
        .execute()
    msgs = db.table("messages") \
        .select("*") \
        .eq("conversation_id", conversation_id) \
        .order("created_at") \
        .execute()
    return {"conversation": conv.data, "messages": msgs.data or []}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    db.table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()
    return {"status": "deleted"}


@router.post("/search")
async def search_memory(body: dict, user_id: str = Depends(get_current_user)):
    from backend.rag import search_rag
    query = body.get("query", "")
    if not query:
        return []
    results = await search_rag(query=query, user_id=user_id)
    return results
