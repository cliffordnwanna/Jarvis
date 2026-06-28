from fastapi import APIRouter, Depends
from backend.auth import get_current_user
from backend.db.postgres import get_supabase
from datetime import datetime, timezone, timedelta
from openai import AsyncOpenAI
import os

router = APIRouter()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@router.get("/morning")
async def morning_briefing(user_id: str = Depends(get_current_user)):
    db = get_supabase()
    now = datetime.now(timezone.utc)
    today = now.date()

    people = db.table("people").select("id, name, birthday, last_contacted_at, strength_signal, circle").eq("user_id", user_id).execute()

    birthdays_soon = []
    overdue = []

    for p in (people.data or []):
        if p.get("birthday"):
            try:
                bday = datetime.strptime(p["birthday"], "%Y-%m-%d").date()
                this_year = bday.replace(year=today.year)
                if this_year < today:
                    this_year = bday.replace(year=today.year + 1)
                days_until = (this_year - today).days
                if 0 <= days_until <= 7:
                    birthdays_soon.append({
                        "name": p["name"],
                        "days_until": days_until,
                        "person_id": p["id"],
                    })
            except Exception:
                pass

        if p.get("strength_signal") in ["cooling", "cold"]:
            overdue.append({
                "name": p["name"],
                "strength": p["strength_signal"],
                "last_contact": p.get("last_contacted_at"),
                "person_id": p["id"],
            })

    events = db.table("relationship_events") \
        .select("*, people(name)") \
        .eq("user_id", user_id) \
        .is_("completed_at", "null") \
        .gte("scheduled_at", now.isoformat()) \
        .lte("scheduled_at", (now + timedelta(hours=24)).isoformat()) \
        .execute()

    goals = db.table("goals") \
        .select("title, urgency, last_touched_at") \
        .eq("user_id", user_id) \
        .eq("status", "active") \
        .execute()

    stale_goals = []
    for g in (goals.data or []):
        if g.get("last_touched_at"):
            last = datetime.fromisoformat(g["last_touched_at"].replace("Z", "+00:00"))
            if (now - last).days >= 5:
                stale_goals.append(g["title"])

    context = f"""
Today is {today.strftime('%A, %B %d')}.

Birthdays soon: {birthdays_soon or 'none'}
People to reconnect with: {[p['name'] for p in overdue[:3]] or 'none'}
Events today: {[e.get('title') for e in (events.data or [])] or 'none'}
Stale goals: {stale_goals[:2] or 'none'}
"""

    try:
        res = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are JARVIS. Write a morning briefing in 4-6 lines max. "
                        "Be warm and direct — like a smart friend who knows your life. "
                        "No bullet points. No headers. Just natural sentences. "
                        "Lead with the most important thing. End with one clear focus for the day."
                    ),
                },
                {"role": "user", "content": context},
            ],
            max_tokens=200,
        )
        briefing_text = res.choices[0].message.content.strip()
    except Exception:
        briefing_text = "Good morning. Here's what needs your attention today."

    return {
        "briefing": briefing_text,
        "birthdays_soon": birthdays_soon,
        "overdue_contacts": overdue[:5],
        "events_today": events.data or [],
        "stale_goals": stale_goals,
        "generated_at": now.isoformat(),
    }
