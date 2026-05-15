"""
Nudge engine — evaluates world state and emits proactive nudge suggestions.

This is the “personality layer” for v1: rule-based, deterministic, fast.
"""

from __future__ import annotations

from datetime import datetime, timezone


def evaluate(world_state: dict, goals: list[dict] | None = None) -> list[dict]:
    """Return a list of nudge dicts to queue, given current world state."""
    goals = goals or []
    nudges: list[dict] = []
    now = datetime.now(timezone.utc)

    temporal = world_state.get("temporal", {}) or {}
    location = world_state.get("location", {}) or {}
    env = world_state.get("environment", {}) or {}
    weather = (env.get("weather") or {}) if isinstance(env.get("weather"), dict) else {}
    bio = world_state.get("biological", {}) or {}
    device = world_state.get("device", {}) or {}

    # Battery low => high priority
    battery_pct = device.get("battery_pct", 100)
    charging = bool(device.get("charging", False))
    if isinstance(battery_pct, (int, float)) and battery_pct < 20 and not charging:
        nudges.append(
            {
                "type": "battery",
                "message": "Battery low — consider charging.",
                "priority": "high",
                "card_data": {"battery_pct": battery_pct, "charging": charging},
            }
        )

    # Rain soon => medium priority
    rain_prob = weather.get("forecast_1h_rain_prob", 0)
    if isinstance(rain_prob, (int, float)) and rain_prob >= 0.7:
        city = location.get("city") or "your area"
        nudges.append(
            {
                "type": "weather",
                "message": f"Rain likely in the next hour ({int(rain_prob * 100)}%). Bring an umbrella.",
                "priority": "medium",
                "card_data": {
                    "condition": weather.get("description") or weather.get("condition") or "rain",
                    "temp_c": weather.get("temp_c"),
                    "feels_like_c": weather.get("feels_like_c"),
                    "humidity_pct": weather.get("humidity_pct"),
                    "rain_prob_1h": int(rain_prob * 100),
                    "city": city,
                },
            }
        )

    # Hunger => medium priority
    hunger_prob = bio.get("hunger_probability", 0)
    if isinstance(hunger_prob, (int, float)) and hunger_prob > 0.75:
        nudges.append(
            {
                "type": "food",
                "message": "You haven't eaten in a while. Time for a meal?",
                "priority": "medium",
                "card_data": {"reason": "High hunger probability", "hunger_probability": hunger_prob},
            }
        )

    # Midday at work => low priority (starter rule)
    if temporal.get("time_of_day") == "midday" and location.get("location_type") == "work":
        nudges.append(
            {
                "type": "food",
                "message": "It’s midday — want a quick lunch option near work?",
                "priority": "low",
                "card_data": {"reason": "Midday at work"},
            }
        )

    # Stale goals => low priority
    stale_goals = (world_state.get("goals") or {}).get("stale_goals")
    if isinstance(stale_goals, list):
        for g in stale_goals:
            if not isinstance(g, dict):
                continue
            name = g.get("name")
            if not name:
                continue
            nudges.append(
                {
                    "type": "goal",
                    "message": f"Goal '{name}' looks stale — want to take one small step today?",
                    "priority": "low",
                    "card_data": {
                        "goal_name": name,
                        "days_stale": g.get("days_since_touched", 3),
                        "urgency": g.get("urgency", "medium"),
                        "suggested_action": "Pick one 10-minute action and do it now.",
                    },
                }
            )
    else:
        for goal in goals:
            if goal.get("status") != "active":
                continue
            last_touched = goal.get("last_touched")
            if not last_touched:
                continue
            try:
                lt = datetime.fromisoformat(str(last_touched).replace("Z", "+00:00"))
                days_stale = (now - lt).days
            except (ValueError, TypeError):
                continue
            if days_stale >= 3:
                nudges.append(
                    {
                        "type": "goal",
                        "message": f"Goal '{goal.get('name', 'Unnamed')}' hasn't been touched in {days_stale} days.",
                        "priority": "low",
                        "card_data": {
                            "goal_name": goal.get("name"),
                            "days_stale": days_stale,
                            "urgency": goal.get("urgency", "medium"),
                            "suggested_action": "Review and take one small step today.",
                        },
                    }
                )

    return nudges

