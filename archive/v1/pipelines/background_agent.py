"""
JARVIS Background Agent Pipeline (Phase 2)
Runs scheduled tasks in the background for proactive assistance.

Features:
- Daily goal check-ins
- News monitoring for topics you care about
- Calendar reminders
- Cost tracking alerts

SETUP: Enable this pipeline in Open WebUI after Phase 1 is working.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Pipeline:
    class Valves(BaseModel):
        enabled: bool = False  # Set to True to activate
        check_interval_hours: int = 24
        daily_checkin_time: str = "09:00"  # 24hr format
        topics_to_monitor: str = "AI,startups,productivity"  # comma-separated
        cost_alert_threshold: float = 50.0  # USD per month

    def __init__(self):
        self.name = "JARVIS Background Agent (Phase 2)"
        self.valves = self.Valves()

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """
        This pipeline doesn't modify user messages.
        Background tasks would run via APScheduler (not implemented yet).
        """
        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """
        Could inject proactive suggestions into responses.
        Example: "By the way, you have a meeting in 30 minutes."
        """
        return body

    # ──────────────────────────────────────────────────────────
    # Phase 2 Implementation (add these methods when ready):
    # ──────────────────────────────────────────────────────────

    # def daily_goal_checkin(self):
    #     """Ask user about progress on goals, update memory"""
    #     pass

    # def monitor_news(self):
    #     """Search for news on topics_to_monitor, summarize"""
    #     pass

    # def check_calendar(self):
    #     """Pull upcoming events, send reminders"""
    #     pass

    # def track_costs(self):
    #     """Query LiteLLM logs, alert if over threshold"""
    #     pass
