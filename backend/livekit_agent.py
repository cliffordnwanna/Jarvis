"""
JARVIS LiveKit Voice Agent — v1.6 compatible
"""
import os
import logging
import httpx
from dotenv import load_dotenv
load_dotenv()

from livekit import agents
from livekit.agents import AgentSession, Agent, JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import RunContext
from livekit.plugins import openai
from backend.db.postgres import get_supabase
from backend.db.cache import cache_get

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


JARVIS_VOICE_PROMPT = """You are JARVIS — a proactive personal AI assistant.
You are in VOICE mode. Rules:
- Keep ALL responses under 2 sentences
- Never use markdown, bullet points, or lists
- Speak naturally, like a smart friend
- Be direct and warm
- You know the user's name and context from the system

{user_context}
"""


class JARVISAgent(Agent):
    def __init__(self, user_id: str, user_context: str):
        self._user_id = user_id
        super().__init__(
            instructions=JARVIS_VOICE_PROMPT.format(user_context=user_context)
        )

    @function_tool
    async def get_weather(self, context: RunContext) -> str:
        """Get the user's current weather, temperature, and location."""
        try:
            ws = await cache_get(self._user_id)
            if not ws:
                return "I don't have your location yet."
            location = ws.get("location", {})
            weather = ws.get("environment", {}).get("weather", {})
            district = location.get("district", "")
            city = location.get("city", "")
            loc = f"{district}, {city}" if district and district != city else city
            temp = weather.get("temp_c")
            condition = weather.get("description", weather.get("condition", ""))
            rain = int((weather.get("forecast_1h_rain_prob") or 0) * 100)
            umbrella = " Take an umbrella." if rain > 50 else ""
            return f"You're in {loc}. It's {temp}°C and {condition}.{umbrella}"
        except Exception as e:
            return f"Couldn't get weather: {e}"

    @function_tool
    async def search_web(self, context: RunContext, query: str) -> str:
        """
        Search the web for current information, news, prices, or facts.

        Args:
            query: The search query
        """
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "Web search is not available."
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_answer=True,
            )
            if response.get("answer"):
                return response["answer"][:300]
            results = response.get("results", [])[:1]
            return results[0].get("content", "No results found.")[:300] if results else "No results."
        except Exception as e:
            return f"Search failed: {e}"

    @function_tool
    async def get_goals(self, context: RunContext) -> str:
        """Get the user's active goals and priorities."""
        try:
            db = get_supabase()
            res = db.table("goals")\
                .select("title, urgency")\
                .eq("user_id", self._user_id)\
                .eq("status", "active")\
                .execute()
            goals = res.data or []
            if not goals:
                return "You don't have any active goals set."
            titles = [g["title"] for g in goals[:3]]
            return f"Your active goals are: {', '.join(titles)}."
        except Exception as e:
            return f"Couldn't get goals: {e}"

    @function_tool
    async def set_reminder(self, context: RunContext, title: str, scheduled_at: str) -> str:
        """
        Set a reminder for the user.

        Args:
            title: What the reminder is about
            scheduled_at: ISO datetime string e.g. 2026-07-01T09:00:00
        """
        try:
            db = get_supabase()
            db.table("relationship_events").insert({
                "user_id": self._user_id,
                "title": title,
                "scheduled_at": scheduled_at,
                "event_type": "reminder",
                "nudge_sent": False,
                "context": {"created_via": "voice"},
            }).execute()
            return f"Done, I've set a reminder to {title}."
        except Exception as e:
            return f"Couldn't set reminder: {e}"

    @function_tool
    async def get_exchange_rate(self, context: RunContext, from_currency: str, to_currency: str) -> str:
        """
        Get current exchange rate between two currencies.

        Args:
            from_currency: Source currency e.g. USD, NGN, GBP
            to_currency: Target currency e.g. NGN, USD, EUR
        """
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"https://open.er-api.com/v6/latest/{from_currency.upper()}",
                    timeout=8.0,
                )
                data = r.json()
                rate = data.get("rates", {}).get(to_currency.upper())
                if rate:
                    return f"1 {from_currency.upper()} equals {rate:.2f} {to_currency.upper()}."
                return "Couldn't find that exchange rate."
        except Exception as e:
            return f"Exchange rate error: {e}"

    @function_tool
    async def calculate(self, context: RunContext, expression: str) -> str:
        """
        Calculate a mathematical expression.

        Args:
            expression: Math expression e.g. "15% of 250000" or "500 * 1650"
        """
        try:
            import ast
            import math
            allowed = {k: v for k, v in math.__dict__.items() if not k.startswith('_')}
            allowed.update({'abs': abs, 'round': round})
            expr = expression.replace('%', '/100').replace(' of ', '*')
            result = eval(
                compile(ast.parse(expr, mode='eval'), '<string>', 'eval'),
                {"__builtins__": {}},
                allowed,
            )
            return f"{expression} equals {result}."
        except Exception as e:
            return f"Couldn't calculate that: {e}"


async def get_user_context(user_id: str) -> str:
    """Fetch user profile and world state for the system prompt."""
    parts = []
    db = get_supabase()
    try:
        profile = db.table("users")\
            .select("display_name, timezone")\
            .eq("id", user_id)\
            .maybe_single()\
            .execute()
        if profile.data and profile.data.get("display_name"):
            parts.append(f"The user's name is {profile.data['display_name']}.")
    except Exception:
        pass
    try:
        ws = await cache_get(user_id)
        if ws:
            city = ws.get("location", {}).get("city", "")
            if city:
                parts.append(f"They are currently in {city}, Nigeria.")
    except Exception:
        pass
    return " ".join(parts)


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    room_name = ctx.room.name
    user_id = room_name.replace("jarvis-", "") if room_name.startswith("jarvis-") else ""

    logger.info(f"[livekit] Room: {room_name}, user: {user_id}")

    user_context = await get_user_context(user_id) if user_id else ""

    session = AgentSession(
        stt=openai.STT(model="whisper-1"),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(voice="alloy"),
    )

    agent = JARVISAgent(user_id=user_id, user_context=user_context)

    await session.start(
        room=ctx.room,
        agent=agent,
    )

    await session.generate_reply(
        instructions="Greet the user by name if you know it, and ask how you can help. One sentence only."
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
