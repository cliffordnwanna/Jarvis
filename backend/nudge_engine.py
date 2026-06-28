from datetime import datetime, timezone, timedelta
from backend.db.postgres import get_supabase


async def evaluate_nudges(world_state: dict, user_id: str) -> list[dict]:
    """Evaluate all nudge conditions and persist any that fire."""
    db = get_supabase()
    nudges = []
    now = datetime.now(timezone.utc)

    # --- WEATHER ---
    weather = world_state.get("environment", {}).get("weather", {})
    rain_prob_1h = weather.get("forecast_1h_rain_prob", 0) or 0
    rain_prob_3h = weather.get("forecast_3h_rain_prob", 0) or 0
    if max(rain_prob_1h, rain_prob_3h) > 0.6:
        pct = int(max(rain_prob_1h, rain_prob_3h) * 100)
        nudges.append({
            "user_id": user_id,
            "nudge_type": "weather",
            "message": f"Rain likely in the next few hours ({pct}% chance). Take an umbrella.",
            "priority": "high",
        })

    # --- GOALS ---
    goals = world_state.get("goals", {}).get("active_goals", [])
    for goal in goals:
        last_touched = goal.get("last_touched_at")
        if last_touched:
            try:
                last_dt = datetime.fromisoformat(last_touched.replace("Z", "+00:00"))
                days_stale = (now - last_dt).days
                if days_stale >= 7:
                    nudges.append({
                        "user_id": user_id,
                        "nudge_type": "goal",
                        "message": f"You haven't made progress on '{goal.get('title', 'a goal')}' in {days_stale} days. Want to pick it up?",
                        "priority": "low" if days_stale < 14 else "medium",
                    })
            except Exception:
                pass

    # --- RELATIONSHIP: BIRTHDAYS ---
    try:
        people_res = db.table("people") \
            .select("id, name, birthday, last_contacted_at, strength_signal, contact_frequency_days") \
            .eq("user_id", user_id) \
            .not_.is_("birthday", "null") \
            .execute()

        for person in (people_res.data or []):
            if not person.get("birthday"):
                continue
            try:
                bday = datetime.strptime(person["birthday"], "%Y-%m-%d")
                now_naive = now.replace(tzinfo=None)
                this_year_bday = bday.replace(year=now.year)
                if this_year_bday < now_naive:
                    this_year_bday = this_year_bday.replace(year=now.year + 1)
                days_until = (this_year_bday - now_naive).days
                if days_until in [7, 2, 1, 0]:
                    label = "today" if days_until == 0 else f"in {days_until} day{'s' if days_until > 1 else ''}"
                    nudges.append({
                        "user_id": user_id,
                        "nudge_type": "relationship_birthday",
                        "person_id": person["id"],
                        "message": f"{person['name']}'s birthday is {label}. Send them a message.",
                        "priority": "high" if days_until <= 1 else "medium",
                    })
            except Exception:
                pass

        # --- RELATIONSHIP: COOLING / COLD ---
        cold_res = db.table("people") \
            .select("id, name, strength_signal, contact_frequency_days") \
            .eq("user_id", user_id) \
            .in_("strength_signal", ["cooling", "cold"]) \
            .execute()

        for person in (cold_res.data or []):
            nudges.append({
                "user_id": user_id,
                "nudge_type": "relationship_cooling",
                "person_id": person["id"],
                "message": f"You haven't connected with {person['name']} in a while. It might be a good time to reach out.",
                "priority": "low",
            })
    except Exception:
        pass

    # Deduplicate: skip nudges already sent in the last 24h with the same type+message
    inserted = []
    for nudge in nudges:
        try:
            recent = db.table("nudge_history") \
                .select("id") \
                .eq("user_id", user_id) \
                .eq("nudge_type", nudge["nudge_type"]) \
                .eq("message", nudge["message"]) \
                .gte("delivered_at", (now - timedelta(hours=24)).isoformat()) \
                .limit(1) \
                .execute()
            if not recent.data:
                db.table("nudge_history").insert({
                    **nudge,
                    "delivered_at": now.isoformat(),
                }).execute()
                inserted.append(nudge)
        except Exception:
            pass

    return inserted
