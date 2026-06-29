import os
import re
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
        print(f"[search] Invalid user_id: {user_id}")
        return []

    db = get_supabase()
    resolved_person_id = person_id
    resolved_person_name = None

    # Stage 1: Score-based person resolution from query text
    if not resolved_person_id:
        try:
            people = db.table("people").select("id, name").eq("user_id", user_id).execute()
            query_lower = query.lower()
            best_match = None
            best_score = 0
            for person in (people.data or []):
                name_lower = person["name"].lower()
                name_parts = name_lower.split()
                if name_lower in query_lower:
                    score = 100
                elif name_parts[0] in query_lower:
                    score = 80
                elif len(name_parts) > 1 and name_parts[-1] in query_lower:
                    score = 70
                else:
                    score = 0
                if score > best_score:
                    best_score = score
                    best_match = person
            if best_match and best_score > 0:
                resolved_person_id = best_match["id"]
                resolved_person_name = best_match["name"]
                print(f"[search] Resolved '{resolved_person_name}' (score={best_score})")
        except Exception as e:
            print(f"[search] Person resolution error: {e}")

    # Stage 2: Hybrid vector + keyword search
    embedding = await embed_text(query)
    if not embedding:
        return []

    try:
        params = {
            "query_text": query,
            "query_embedding": "[" + ",".join(f"{x:.8f}" for x in embedding) + "]",
            "match_user_id": user_id,
            "semantic_weight": 0.7,
            "keyword_weight": 0.3,
            "match_count": 8,
        }
        if resolved_person_id:
            params["match_person_id"] = resolved_person_id
        res = db.rpc("hybrid_search_notes", params).execute()
        results = res.data or []

        # Stage 3: Prepend person profile as context when searching for a specific person
        if resolved_person_id and results:
            try:
                profile = db.table("people")\
                    .select("name, relationship_type, circle, birthday, last_contacted_at, strength_signal")\
                    .eq("id", resolved_person_id)\
                    .single()\
                    .execute()
                if profile.data:
                    p = profile.data
                    results.insert(0, {
                        "content": (
                            f"Profile: {p['name']} is a {p['relationship_type']} ({p['circle']} circle). "
                            f"Last contacted: {p.get('last_contacted_at', 'unknown')}. "
                            f"Relationship strength: {p.get('strength_signal', 'unknown')}."
                        ),
                        "person_id": resolved_person_id,
                        "score": 1.0,
                        "created_at": None,
                    })
            except Exception:
                pass

        print(f"[search] {len(results)} results for query='{query[:50]}' person={resolved_person_name}")
        return results
    except Exception as e:
        print(f"[search] Hybrid search error: {e}")
        return []


@tool
async def add_person(
    user_id: str,
    name: str,
    relationship_type: str = "friend",
    notes: str = None,
    birthday: str = None,
    job: str = None,
) -> dict:
    """
    Add a new person to the user's relationship network.
    Use when the user says 'add X to my people', 'remember my friend X', 'I have a colleague named X', etc.
    Args:
        user_id: authenticated user UUID
        name: person's full name
        relationship_type: one of friend, family, colleague, mentor, acquaintance
        notes: any details about them (job, personality, context)
        birthday: ISO date string YYYY-MM-DD if mentioned
        job: their job title or profession if mentioned
    """
    db = get_supabase()
    try:
        person_data = {
            "user_id": user_id,
            "name": name,
            "relationship_type": relationship_type,
            "circle": "inner" if relationship_type in ["family", "friend"] else "community",
            "tags": [job] if job else [],
        }
        if birthday:
            person_data["birthday"] = birthday

        res = db.table("people").insert(person_data).execute()
        if not res.data:
            return {"status": "error", "detail": "Insert returned no data"}

        person = res.data[0]
        person_id = person["id"]

        if notes or job:
            note_content = notes or f"{name} works as {job}."
            try:
                embedding = await embed_text(note_content)
                note_row = {
                    "user_id": user_id,
                    "person_id": person_id,
                    "content": note_content,
                    "source": "chat_extraction",
                }
                if embedding:
                    note_row["embedding"] = embedding
                db.table("relationship_notes").insert(note_row).execute()
            except Exception as e:
                print(f"[add_person] note insert failed (non-fatal): {e}")

        print(f"[add_person] Added {name} (id={person_id})")
        return {"status": "added", "person_id": person_id, "name": name}
    except Exception as e:
        print(f"[add_person] error: {e}")
        return {"status": "error", "detail": str(e)}


@tool
async def add_note_for_person(
    user_id: str,
    person_name: str,
    note: str,
) -> dict:
    """
    Add a note or detail about someone already in the user's people.
    Use when the user says 'note that Vincent likes chess', 'remember that Sarah got promoted', etc.
    Args:
        user_id: authenticated user UUID
        person_name: name of the person (will be looked up)
        note: the detail to remember
    """
    db = get_supabase()
    try:
        res = db.table("people").select("id, name").eq("user_id", user_id).ilike("name", f"%{person_name}%").limit(1).execute()
        if not res.data:
            return {"status": "error", "detail": f"No person named '{person_name}' found. Add them first."}

        person = res.data[0]
        embedding = await embed_text(note)
        note_row = {
            "user_id": user_id,
            "person_id": person["id"],
            "content": note,
            "source": "chat_extraction",
        }
        if embedding:
            note_row["embedding"] = embedding
        db.table("relationship_notes").insert(note_row).execute()
        return {"status": "noted", "person": person["name"], "note": note}
    except Exception as e:
        print(f"[add_note_for_person] error: {e}")
        return {"status": "error", "detail": str(e)}


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
    event_type: str = "reminder",
) -> dict:
    """
    Create a reminder or future event for the user.
    Use when the user says: 'remind me to...', 'don't let me forget', 'call X on Friday', etc.
    Args:
        user_id: the authenticated user's UUID
        title: what to remind about
        scheduled_at: ISO 8601 datetime string — convert natural language to exact datetime
                      ('tomorrow at 9am' → next day 09:00 UTC, 'in 2 hours' → now + 2h)
        person_name: optional name of a person this reminder is about
        event_type: one of: reminder, task, call, meeting, follow_up, check_in, occasion, birthday
                    Use "reminder" for general reminders, "task" for work tasks, "call" for calls.
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

    # Guard: remap any unrecognised event_type to reminder
    VALID_EVENT_TYPES = {"birthday", "follow_up", "call", "meeting", "occasion", "check_in", "reminder", "task"}
    if event_type not in VALID_EVENT_TYPES:
        event_type = "reminder"

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
