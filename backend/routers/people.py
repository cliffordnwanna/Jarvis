from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from backend.auth import get_current_user
from backend.db.postgres import get_supabase

router = APIRouter()


class PersonCreate(BaseModel):
    name: str
    relationship_type: str = "friend"
    circle: str = "community"
    birthday: Optional[str] = None
    contact_frequency_days: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tags: list[str] = []


class NoteCreate(BaseModel):
    content: str
    source: str = "text"


class EventCreate(BaseModel):
    event_type: str
    title: str
    scheduled_at: str
    context: dict = {}


class InteractionLog(BaseModel):
    interaction_type: str
    notes: Optional[str] = None
    occurred_at: Optional[str] = None


@router.get("")
async def list_people(
    circle: Optional[str] = None,
    strength: Optional[str] = None,
    user_id: str = Depends(get_current_user),
):
    db = get_supabase()
    q = db.table("people").select("*").eq("user_id", user_id)
    if circle:
        q = q.eq("circle", circle)
    if strength:
        q = q.eq("strength_signal", strength)
    res = q.order("name").execute()
    return res.data or []


@router.post("")
async def create_person(person: PersonCreate, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    data = {**person.model_dump(), "user_id": user_id}
    res = db.table("people").insert(data).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create person")
    return res.data[0]


@router.get("/overdue")
async def overdue_people(user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("people") \
        .select("*") \
        .eq("user_id", user_id) \
        .in_("strength_signal", ["cooling", "cold"]) \
        .order("last_contacted_at", nullsfirst=True) \
        .execute()
    return res.data or []


@router.post("/search")
async def search_people_notes(body: dict, user_id: str = Depends(get_current_user)):
    from backend.tools.relationship_tools import hybrid_search_notes
    query = body.get("query", "")
    if not query:
        return []
    results = await hybrid_search_notes(query=query, user_id=user_id)
    return results


@router.get("/{person_id}")
async def get_person(person_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("people").select("*").eq("id", person_id).eq("user_id", user_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Person not found")

    notes = db.table("relationship_notes") \
        .select("id, content, extracted_facts, source, created_at") \
        .eq("person_id", person_id) \
        .order("created_at", desc=True) \
        .limit(20) \
        .execute()

    events = db.table("relationship_events") \
        .select("*") \
        .eq("person_id", person_id) \
        .is_("completed_at", "null") \
        .order("scheduled_at") \
        .limit(10) \
        .execute()

    return {
        **res.data,
        "recent_notes": notes.data or [],
        "upcoming_events": events.data or [],
    }


@router.patch("/{person_id}")
async def update_person(person_id: str, updates: dict, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = db.table("people").update(updates).eq("id", person_id).eq("user_id", user_id).execute()
    return res.data[0] if res.data else {}


@router.delete("/{person_id}")
async def delete_person(person_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    db.table("people").delete().eq("id", person_id).eq("user_id", user_id).execute()
    return {"status": "deleted"}


@router.get("/{person_id}/notes")
async def list_notes(person_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("relationship_notes") \
        .select("*") \
        .eq("person_id", person_id) \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .execute()
    return res.data or []


@router.post("/{person_id}/notes")
async def add_note(person_id: str, note: NoteCreate, user_id: str = Depends(get_current_user)):
    from backend.tools.relationship_tools import extract_facts_from_note, embed_text
    db = get_supabase()

    facts = await extract_facts_from_note(note.content, person_id)
    embedding = await embed_text(note.content)

    data = {
        "user_id": user_id,
        "person_id": person_id,
        "content": note.content,
        "extracted_facts": facts,
        "source": note.source,
    }
    if embedding:
        data["embedding"] = embedding

    res = db.table("relationship_notes").insert(data).execute()

    db.table("people").update({
        "last_contacted_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", person_id).execute()

    return res.data[0] if res.data else {}


@router.get("/{person_id}/events")
async def list_events(person_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    res = db.table("relationship_events") \
        .select("*") \
        .eq("person_id", person_id) \
        .eq("user_id", user_id) \
        .order("scheduled_at") \
        .execute()
    return res.data or []


@router.post("/{person_id}/events")
async def create_event(person_id: str, event: EventCreate, user_id: str = Depends(get_current_user)):
    db = get_supabase()
    data = {**event.model_dump(), "person_id": person_id, "user_id": user_id}
    res = db.table("relationship_events").insert(data).execute()
    return res.data[0] if res.data else {}


@router.post("/{person_id}/log")
async def log_interaction(
    person_id: str,
    interaction: InteractionLog,
    user_id: str = Depends(get_current_user),
):
    db = get_supabase()
    occurred = interaction.occurred_at or datetime.now(timezone.utc).isoformat()
    db.table("interaction_log").insert({
        "user_id": user_id,
        "person_id": person_id,
        "interaction_type": interaction.interaction_type,
        "notes": interaction.notes,
        "occurred_at": occurred,
    }).execute()
    db.table("people").update({
        "last_contacted_at": occurred,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", person_id).execute()
    return {"status": "logged"}


@router.get("/suggest-message/{person_id}")
async def suggest_message(person_id: str, user_id: str = Depends(get_current_user)):
    from backend.tools.relationship_tools import generate_message_suggestion
    msg = await generate_message_suggestion(person_id=person_id, user_id=user_id)
    return {"suggestion": msg}
