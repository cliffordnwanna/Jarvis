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


def start_scheduler():
    scheduler.add_job(check_due_events, "interval", minutes=5, id="check_due_events", replace_existing=True)
    scheduler.add_job(check_birthdays, "cron", hour=8, minute=0, id="check_birthdays", replace_existing=True)
    scheduler.add_job(recompute_strength_signals, "cron", hour=0, minute=0, id="recompute_strength_signals", replace_existing=True)
    scheduler.start()
    logger.info("[scheduler] Started — checking reminders every 5 minutes, birthdays at 8am UTC")
