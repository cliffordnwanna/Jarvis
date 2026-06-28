import os
import json
from openai import AsyncOpenAI
from langchain_core.tools import tool
from backend.db.postgres import get_supabase

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def embed_text(text: str) -> list[float] | None:
    """Generate OpenAI embedding for a text string."""
    try:
        res = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],
        )
        return res.data[0].embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


async def extract_facts_from_note(content: str, person_id: str) -> list[dict]:
    """Use GPT-4o-mini to extract structured facts from a freeform note."""
    try:
        res = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        'Extract structured facts from the note about a person. '
                        'Return JSON: {"facts": [{"type": string, "value": string, "date": string|null}]}. '
                        'Types: job_change, location, health, relationship, interest, preference, milestone, other.'
                    ),
                },
                {"role": "user", "content": content},
            ],
            max_tokens=500,
        )
        data = json.loads(res.choices[0].message.content)
        return data.get("facts", [])
    except Exception as e:
        print(f"Fact extraction error: {e}")
        return []


async def generate_message_suggestion(person_id: str, user_id: str) -> str:
    """Generate a contextually appropriate first message to send to a person."""
    db = get_supabase()

    person_res = db.table("people").select("*").eq("id", person_id).single().execute()
    if not person_res.data:
        return "Hey, just thinking of you. Hope you're doing well!"

    person = person_res.data

    notes_res = db.table("relationship_notes") \
        .select("content, extracted_facts, created_at") \
        .eq("person_id", person_id) \
        .order("created_at", desc=True) \
        .limit(5) \
        .execute()
    notes = notes_res.data or []

    events_res = db.table("relationship_events") \
        .select("*") \
        .eq("person_id", person_id) \
        .is_("completed_at", "null") \
        .order("scheduled_at") \
        .limit(3) \
        .execute()
    events = events_res.data or []

    context = f"""Person: {person['name']} ({person['relationship_type']}, {person['circle']} circle)
Last contacted: {person.get('last_contacted_at', 'unknown')}
Strength signal: {person['strength_signal']}

Recent notes:
{chr(10).join([f'- {n["content"]}' for n in notes]) or 'None'}

Upcoming events:
{chr(10).join([f'- {e["event_type"]}: {e["title"]}' for e in events]) or 'None'}"""

    try:
        res = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Generate a short, warm, natural first message to send to this person. Use context from the notes. Sound like a real friend, not a template. 1-3 sentences max.",
                },
                {"role": "user", "content": context},
            ],
            max_tokens=150,
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return f"Hey {person['name']}, just thinking of you. How have you been?"


import re as _re
_UUID_RE = _re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', _re.I)

async def hybrid_search_notes(query: str, user_id: str, person_id: str = None) -> list[dict]:
    """Hybrid search: semantic vector + keyword ranking combined (Vellum-style)."""
    if not _UUID_RE.match(str(user_id)):
        print(f"Hybrid search skipped: invalid user_id '{user_id}'")
        return []
    embedding = await embed_text(query)
    if not embedding:
        return []

    db = get_supabase()
    try:
        params = {
            "query_text": query,
            "query_embedding": "[" + ",".join(f"{x:.8f}" for x in embedding) + "]",
            "match_user_id": user_id,
            "semantic_weight": 0.7,
            "keyword_weight": 0.3,
            "match_count": 8,
        }
        if person_id:
            params["match_person_id"] = person_id
        res = db.rpc("hybrid_search_notes", params).execute()
        return res.data or []
    except Exception as e:
        print(f"Hybrid search error: {e}")
        return []


@tool
async def hybrid_search_notes_tool(query: str, user_id: str, person_id: str = None) -> list[dict]:
    """
    Search relationship memory using hybrid semantic + keyword ranking.
    Use this when the user mentions a person by name or asks what you know about someone.
    Args:
        query: natural language query about a person or memory
        user_id: the authenticated user's ID
        person_id: optional — restrict search to one person
    """
    return await hybrid_search_notes(query=query, user_id=user_id, person_id=person_id)


@tool
async def create_reminder(
    user_id: str,
    title: str,
    scheduled_at: str,
    person_name: str = None,
    event_type: str = "check_in",
) -> dict:
    """
    Create a reminder or timer for the user.
    Use when the user says: 'remind me to...', 'set a timer for...', 'don't let me forget',
    'call X on Friday', 'check on Y tomorrow', etc.
    Args:
        user_id: the authenticated user's UUID
        title: what to remind about
        scheduled_at: ISO 8601 datetime string — convert natural language to exact datetime
                      ('tomorrow at 9am' → next day 09:00 UTC, 'in 2 hours' → now + 2h)
        person_name: optional name of a person this reminder is about
        event_type: one of: check_in, call, follow_up, birthday, reminder
    """
    db = get_supabase()

    person_id = None
    if person_name:
        try:
            res = db.table("people")\
                .select("id")\
                .eq("user_id", user_id)\
                .ilike("name", f"%{person_name}%")\
                .limit(1)\
                .execute()
            if res.data:
                person_id = res.data[0]["id"]
        except Exception as e:
            print(f"[create_reminder] person lookup error: {e}")

    try:
        row = {
            "user_id": user_id,
            "title": title,
            "scheduled_at": scheduled_at,
            "event_type": event_type,
            "nudge_sent": False,
            "context": {"created_via": "agent"},
        }
        if person_id:
            row["person_id"] = person_id

        print(f"[create_reminder] inserting: {row}")
        res = db.table("relationship_events").insert(row).execute()
        print(f"[create_reminder] result: {res.data}")
    except Exception as e:
        print(f"[create_reminder] INSERT ERROR: {e}")
        return {"status": "error", "detail": str(e)}

    return {
        "status": "reminder_created",
        "title": title,
        "scheduled_at": scheduled_at,
        "person": person_name or "general",
    }
