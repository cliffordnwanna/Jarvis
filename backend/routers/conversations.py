from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.auth import get_current_user
from backend.db.postgres import get_supabase

router = APIRouter()


class ConversationCreate(BaseModel):
    id: Optional[str] = None  # client-generated UUID, becomes the LangGraph thread_id


class ConversationUpdate(BaseModel):
    title: str


@router.post("")
async def create_conversation(body: ConversationCreate, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    row = {"user_id": user_id, "title": "New conversation"}
    if body.id:
        row["id"] = body.id
    res = db.table("conversations").insert(row).execute()
    return res.data[0] if res.data else {}


@router.get("")
async def list_conversations(user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("conversations")\
        .select("id, title, created_at, last_message_at")\
        .eq("user_id", user_id)\
        .order("last_message_at", desc=True)\
        .execute()
    return res.data or []


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("conversations")\
        .select("id, title, created_at, last_message_at")\
        .eq("id", conversation_id)\
        .eq("user_id", user_id)\
        .maybe_single()\
        .execute()
    if not res or not res.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return res.data


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("messages")\
        .select("role, content, created_at")\
        .eq("conversation_id", conversation_id)\
        .eq("user_id", user_id)\
        .order("created_at", desc=False)\
        .execute()
    return {"messages": res.data or []}


@router.patch("/{conversation_id}")
async def update_conversation(conversation_id: str, body: ConversationUpdate, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("conversations")\
        .update({"title": body.title})\
        .eq("id", conversation_id)\
        .eq("user_id", user_id)\
        .execute()
    return res.data[0] if res.data else {}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    db.table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()
    return {"status": "deleted"}
