import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.db.postgres import get_supabase

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_due_events():
    """Runs every 5 minutes. Creates nudges for due relationship events."""
    db = get_supabase()
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(minutes=10)

    try:
        events = db.table("relationship_events")\
            .select("*, people(name, id)")\
            .eq("nudge_sent", False)\
            .is_("completed_at", "null")\
            .lte("scheduled_at", window_end.isoformat())\
            .execute()

        for event in (events.data or []):
            try:
                person_name = (event.get("people") or {}).get("name", "someone")
                event_type = event.get("event_type", "reminder")
                title = event.get("title", "")
                context = event.get("context") or {}
                user_id = event.get("user_id")

                if event_type == "birthday":
                    message = f"🎂 It's {person_name}'s birthday today! {context.get('message_suggestion', 'Send them a message.')}"
                    priority = "high"
                elif event_type == "follow_up":
                    message = f"Follow-up: {title}. {context.get('reason', '')}"
                    priority = "medium"
                elif event_type == "call":
                    message = f"📞 Reminder to call {person_name}. {title}"
                    priority = "medium"
                elif event_type == "check_in":
                    message = f"👋 Time to check in with {person_name}. {title}"
                    priority = "low"
                else:
                    message = f"⏰ Reminder: {title}"
                    priority = "medium"

                db.table("nudge_history").insert({
                    "user_id": user_id,
                    "nudge_type": f"relationship_{event_type}",
                    "person_id": event.get("person_id"),
                    "message": message,
                    "priority": priority,
                    "delivered_at": now.isoformat(),
                }).execute()

                db.table("relationship_events")\
                    .update({"nudge_sent": True})\
                    .eq("id", event["id"])\
                    .execute()

                logger.info(f"[scheduler] Nudge sent for event {event['id']}: {message[:60]}")

            except Exception as e:
                logger.error(f"[scheduler] Error processing event {event.get('id')}: {e}")

    except Exception as e:
        logger.error(f"[scheduler] check_due_events error: {e}")


async def check_birthdays():
    """Runs daily at 8am UTC. Creates birthday nudges for today, 2 days, 7 days out."""
    db = get_supabase()
    now = datetime.now(timezone.utc)
    today = now.date()

    try:
        people = db.table("people")\
            .select("id, user_id, name, birthday")\
            .not_.is_("birthday", "null")\
            .execute()

        for person in (people.data or []):
            try:
                bday_str = person.get("birthday")
                if not bday_str:
                    continue

                bday = datetime.strptime(bday_str, "%Y-%m-%d").date()
                this_year = bday.replace(year=today.year)
                if this_year < today:
                    this_year = bday.replace(year=today.year + 1)

                days_until = (this_year - today).days
                if days_until not in [0, 2, 7]:
                    continue

                existing = db.table("nudge_history")\
                    .select("id")\
                    .eq("user_id", person["user_id"])\
                    .eq("person_id", person["id"])\
                    .eq("nudge_type", "relationship_birthday")\
                    .gte("delivered_at", now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat())\
                    .execute()

                if existing.data:
                    continue

                if days_until == 0:
                    message = f"🎂 Today is {person['name']}'s birthday! Send them a message."
                    priority = "high"
                elif days_until == 2:
                    message = f"🎂 {person['name']}'s birthday is in 2 days."
                    priority = "medium"
                else:
                    message = f"🎂 {person['name']}'s birthday is in 7 days."
                    priority = "low"

                db.table("nudge_history").insert({
                    "user_id": person["user_id"],
                    "nudge_type": "relationship_birthday",
                    "person_id": person["id"],
                    "message": message,
                    "priority": priority,
                    "delivered_at": now.isoformat(),
                }).execute()

                logger.info(f"[scheduler] Birthday nudge: {person['name']} in {days_until} days")

            except Exception as e:
                logger.error(f"[scheduler] Birthday error for {person.get('name')}: {e}")

    except Exception as e:
        logger.error(f"[scheduler] check_birthdays error: {e}")


async def recompute_strength_signals():
    """Runs nightly. Updates warm/cooling/cold signals for all people."""
    db = get_supabase()
    try:
        db.rpc("recompute_strength_signals").execute()
        logger.info("[scheduler] Strength signals recomputed")
    except Exception as e:
        logger.error(f"[scheduler] Strength signal error: {e}")


async def morning_weather_briefing():
    """
    Runs at 3:00am Lagos time (2:00 UTC) every day.
    Sends one nudge per user covering: weather, birthdays, overdue contacts, stale goals.
    Uses GPT-4o-mini to write the final message naturally.
    """
    import httpx
    import os
    from openai import AsyncOpenAI
    from backend.db.postgres import get_supabase

    db = get_supabase()
    oai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    now = datetime.now(timezone.utc)
    today = now.date()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        users = db.table("users").select("id, home_lat, home_lng, timezone").execute()
    except Exception as e:
        logger.error(f"[scheduler] morning_briefing: could not fetch users: {e}")
        return

    for user in (users.data or []):
        user_id = user["id"]
        lat = user.get("home_lat")
        lng = user.get("home_lng")

        # Fallback: pull coords from world_state cache
        if not lat or not lng:
            try:
                ws = db.table("world_state").select("state").eq("user_id", user_id).maybe_single().execute()
                if ws and ws.data:
                    state = ws.data.get("state", {})
                    lat = state.get("_meta", {}).get("lat")
                    lng = state.get("_meta", {}).get("lng")
            except Exception:
                pass

        # Skip if already sent today
        try:
            existing = db.table("nudge_history")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("nudge_type", "morning_briefing")\
                .gte("delivered_at", today_start.isoformat())\
                .execute()
            if existing.data:
                logger.info(f"[scheduler] morning_briefing already sent to {user_id} today")
                continue
        except Exception:
            pass

        sections = []

        # ── SECTION 1: WEATHER ──────────────────────────────────────────
        if lat and lng:
            try:
                async with httpx.AsyncClient(timeout=8.0) as http:
                    r = await http.get(
                        "https://api.open-meteo.com/v1/forecast",
                        params={
                            "latitude": lat,
                            "longitude": lng,
                            "current": "temperature_2m,weathercode,precipitation",
                            "hourly": "precipitation_probability",
                            "daily": "temperature_2m_max,precipitation_probability_max,weathercode",
                            "forecast_days": 2,
                            "timezone": "auto",
                        },
                    )
                    data = r.json()

                current = data.get("current", {})
                hourly  = data.get("hourly", {})
                daily   = data.get("daily", {})

                temp         = current.get("temperature_2m")
                precip       = current.get("precipitation", 0) or 0
                rain_probs   = hourly.get("precipitation_probability", [])
                max_rain     = max(rain_probs[:10], default=0)
                tomorrow_max = (daily.get("temperature_2m_max") or [None, None])[1]
                tomorrow_rain = (daily.get("precipitation_probability_max") or [0, 0])[1] or 0

                wmo = current.get("weathercode", 0)
                if wmo == 0: condition = "clear"
                elif wmo in [1, 2, 3]: condition = "partly cloudy"
                elif wmo in [45, 48]: condition = "foggy"
                elif wmo in [51, 53, 55, 61, 63, 65, 80, 81, 82]: condition = "rainy"
                elif wmo in [95, 96, 99]: condition = "thunderstorm"
                else: condition = "cloudy"

                wx = f"Today: {temp}°C, {condition}."
                if precip > 0.1:
                    wx += " It's already raining — take an umbrella."
                elif max_rain > 50:
                    wx += f" Rain likely later ({max_rain}%) — take an umbrella."
                if tomorrow_max:
                    wx += f" Tomorrow: {tomorrow_max}°C"
                    if tomorrow_rain > 50:
                        wx += f", rain likely ({tomorrow_rain}%)"
                    wx += "."

                sections.append(wx)
            except Exception as e:
                logger.error(f"[scheduler] morning_briefing weather error for {user_id}: {e}")

        # ── SECTION 2: BIRTHDAYS ────────────────────────────────────────
        try:
            people = db.table("people")\
                .select("id, name, birthday")\
                .eq("user_id", user_id)\
                .not_.is_("birthday", "null")\
                .execute()

            birthday_lines = []
            for person in (people.data or []):
                try:
                    bday = datetime.strptime(person["birthday"], "%Y-%m-%d").date()
                    this_year = bday.replace(year=today.year)
                    if this_year < today:
                        this_year = bday.replace(year=today.year + 1)
                    days_until = (this_year - today).days
                    if days_until == 0:
                        birthday_lines.append(f"🎂 Today is {person['name']}'s birthday!")
                    elif days_until == 1:
                        birthday_lines.append(f"🎂 {person['name']}'s birthday is tomorrow.")
                    elif days_until == 2:
                        birthday_lines.append(f"🎂 {person['name']}'s birthday is in 2 days.")
                except Exception:
                    pass

            if birthday_lines:
                sections.append(" ".join(birthday_lines))
        except Exception as e:
            logger.error(f"[scheduler] morning_briefing birthdays error for {user_id}: {e}")

        # ── SECTION 3: OVERDUE CONTACTS ─────────────────────────────────
        try:
            overdue_res = db.table("people")\
                .select("name, strength_signal, contact_frequency_days, last_contacted_at")\
                .eq("user_id", user_id)\
                .in_("strength_signal", ["cooling", "cold"])\
                .limit(3)\
                .execute()

            if overdue_res.data:
                names = [p["name"] for p in overdue_res.data]
                if len(names) == 1:
                    sections.append(f"👥 Reach out today: {names[0]} is going cold.")
                else:
                    sections.append(f"👥 People to reconnect with: {', '.join(names)}.")
        except Exception as e:
            logger.error(f"[scheduler] morning_briefing overdue error for {user_id}: {e}")

        # ── SECTION 4: STALE GOALS ──────────────────────────────────────
        try:
            goals_res = db.table("goals")\
                .select("title, last_touched_at, urgency")\
                .eq("user_id", user_id)\
                .eq("status", "active")\
                .execute()

            stale = []
            for g in (goals_res.data or []):
                last = g.get("last_touched_at")
                if last:
                    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                    if (now - last_dt).days >= 5:
                        stale.append(g["title"])
                else:
                    stale.append(g["title"])

            if stale:
                if len(stale) == 1:
                    sections.append(f"🎯 Goal needing attention: {stale[0]}.")
                else:
                    sections.append(f"🎯 Goals needing attention: {', '.join(stale[:2])}.")
        except Exception as e:
            logger.error(f"[scheduler] morning_briefing goals error for {user_id}: {e}")

        # ── ASSEMBLE & POLISH WITH GPT-4o-mini ──────────────────────────
        if not sections:
            logger.info(f"[scheduler] morning_briefing: nothing to report for {user_id}")
            continue

        # Determine correct greeting from user's local time
        user_tz_str = user.get("timezone") or "UTC"
        try:
            from zoneinfo import ZoneInfo
            local_hour = datetime.now(ZoneInfo(user_tz_str)).hour
        except Exception:
            local_hour = now.hour
        if local_hour < 12:
            greeting = "Good morning"
        elif local_hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        raw = " ".join(sections)
        try:
            res = await oai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are JARVIS. Rewrite this briefing in 2-4 short natural sentences. "
                            f"Warm, direct, like a smart friend. No bullet points. No headers. "
                            f"Keep all the facts. Start with '{greeting}.' (use exactly this greeting, not a different one)."
                        ),
                    },
                    {"role": "user", "content": raw},
                ],
                max_tokens=200,
            )
            final_message = res.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[scheduler] morning_briefing GPT polish failed: {e}")
            final_message = f"{greeting}. " + raw

        try:
            db.table("nudge_history").insert({
                "user_id": user_id,
                "nudge_type": "morning_briefing",
                "message": final_message,
                "priority": "high",
                "delivered_at": now.isoformat(),
            }).execute()
            logger.info(f"[scheduler] Morning briefing sent to {user_id}: {final_message[:100]}")
        except Exception as e:
            logger.error(f"[scheduler] morning_briefing insert error for {user_id}: {e}")


def start_scheduler():
    scheduler.add_job(check_due_events, "interval", minutes=5, id="check_due_events", replace_existing=True)
    scheduler.add_job(check_birthdays, "cron", hour=8, minute=0, id="check_birthdays", replace_existing=True)
    scheduler.add_job(recompute_strength_signals, "cron", hour=0, minute=0, id="recompute_strength_signals", replace_existing=True)
    # 3:00am Lagos time = 2:00am UTC (Lagos is UTC+1)
    scheduler.add_job(morning_weather_briefing, "cron", hour=2, minute=0, id="morning_weather_briefing", replace_existing=True)
    scheduler.start()
    logger.info("[scheduler] Started — reminders every 5min, birthdays 8am UTC, morning briefing 2:00am UTC (3am Lagos)")
