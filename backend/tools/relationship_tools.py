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
    """Hybrid search: semantic vector + keyword ranking combined (Vellum-style).

    STRICT ISOLATION: if a person is identified in the query, ONLY their data
    is returned — never another person's notes as a fallback.
    """
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
                print(f"[search] Resolved: {resolved_person_name} (score={best_score})")
        except Exception as e:
            print(f"[search] Person resolution error: {e}")

    # Stage 2: Specific person identified — return ONLY their data, never fall through
    if resolved_person_id:
        results = []

        # Always fetch their profile
        try:
            profile_res = db.table("people")\
                .select("*")\
                .eq("id", resolved_person_id)\
                .single()\
                .execute()
            if profile_res.data:
                p = profile_res.data
                parts = [f"{p['name']} is your {p['relationship_type']}"]
                if p.get("birthday"):
                    parts.append(f"birthday {p['birthday']}")
                if p.get("last_contacted_at"):
                    parts.append(f"last contacted {p['last_contacted_at'][:10]}")
                parts.append(f"relationship strength: {p.get('strength_signal', 'unknown')}")
                results.append({
                    "content": ". ".join(parts) + ".",
                    "person_id": resolved_person_id,
                    "score": 1.0,
                    "created_at": None,
                    "type": "profile",
                })
        except Exception as e:
            print(f"[search] Profile fetch error: {e}")

        # Search their notes (person-scoped — never bleeds into other people)
        try:
            embedding = await embed_text(query)
            if embedding:
                params = {
                    "query_text": query,
                    "query_embedding": "[" + ",".join(f"{x:.8f}" for x in embedding) + "]",
                    "match_user_id": user_id,
                    "match_person_id": resolved_person_id,
                    "semantic_weight": 0.7,
                    "keyword_weight": 0.3,
                    "match_count": 5,
                }
                res = db.rpc("hybrid_search_notes", params).execute()
                notes = res.data or []
                results.extend(notes)
                print(f"[search] {resolved_person_name}: {len(notes)} notes")
        except Exception as e:
            print(f"[search] Notes search error: {e}")

        # CRITICAL: always return here — never fall through to general search
        if not results:
            return [{
                "content": "No information found for this person.",
                "person_id": resolved_person_id,
                "score": 0.0,
                "created_at": None,
                "type": "empty",
            }]
        return results

    # Stage 3: No specific person identified — general search across all notes
    try:
        embedding = await embed_text(query)
        if not embedding:
            return []
        params = {
            "query_text": query,
            "query_embedding": "[" + ",".join(f"{x:.8f}" for x in embedding) + "]",
            "match_user_id": user_id,
            "semantic_weight": 0.7,
            "keyword_weight": 0.3,
            "match_count": 8,
        }
        res = db.rpc("hybrid_search_notes", params).execute()
        results = res.data or []
        print(f"[search] General search: {len(results)} results for '{query[:50]}'")
        return results
    except Exception as e:
        print(f"[search] General search error: {e}")
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
    Add a new person to the user's relationship memory.

    CALL THIS when the user:
    - "Add X to my people"
    - "Remember my friend/colleague/sister X"
    - Mentions someone new they want JARVIS to remember
    - Introduces a person: "This is X, she is my..."

    relationship_type: friend, family, colleague, mentor, acquaintance
    notes: any details about them (role, context, how you know them)
    birthday: ISO format YYYY-MM-DD if mentioned
    job: their profession or role

    After adding, immediately call add_note_for_person if any details were shared.
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
    Save a note or memory about a specific person.

    ALWAYS CALL THIS when the user shares ANY information about a person:
    - "Cherry just got a new job"
    - "Vincent is good with hardware"
    - "Malik's presentation went well"
    - "David's mum is in hospital"
    - Any fact, update, or detail about someone

    This is how JARVIS builds its memory of people.
    Never acknowledge information about a person without saving it here.

    person_name: the person's name as stored (must match exactly)
    note: full detail of what was shared, in complete sentences
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
    Search relationship memory for information about a person or topic.

    ALWAYS CALL THIS before answering any question about a person:
    - "What do you know about Cherry?"
    - "Tell me about Vincent"
    - "What did Nnenna say about her job?"
    - "When did I last talk to Malik?"
    - Any question involving a person's name

    Uses hybrid semantic + keyword search for accurate retrieval.
    Returns the person's profile and any notes stored about them.
    If no notes found, returns a clear indication so you can say
    "I don't have notes on [name] yet" rather than guessing.

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
    Create a future reminder or event that will fire as a nudge.

    CALL THIS when user says:
    - "Remind me to X"
    - "Don't forget to X"
    - "Set a reminder for X"
    - "Add X to my schedule"
    - Any request about a future action with a specific time

    IMPORTANT: Use the exact ISO dates from the world context injected above.
    Do NOT calculate dates yourself — use pre-computed values:
    - "tomorrow at 9am"  → use TOMORROW_ISO + "T09:00:00"
    - "next Monday at 3pm" → use NEXT_MONDAY_ISO + "T15:00:00"

    event_type options: reminder, task, call, meeting, follow_up, check_in
    person_name: optional — links reminder to a person in relationship memory
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
