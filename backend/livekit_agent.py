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


JARVIS_VOICE_PROMPT = """You are JARVIS, a voice AI assistant.
Voice mode rules:
- Maximum 2 short sentences per response
- No markdown, no lists, no bullet points
- Natural conversational speech only
- Be warm and direct

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

    @function_tool
    async def add_person_to_network(
        self,
        context: RunContext,
        name: str,
        relationship_type: str,
        notes: str = None,
        birthday: str = None,
    ) -> str:
        """
        Add a new person to the user's relationship memory.
        Call this when the user says things like:
        'add X to my people', 'remember my friend X',
        'X is my colleague', 'meet my sister X'.

        Args:
            name: The person's full name
            relationship_type: friend, family, colleague, mentor, or acquaintance
            notes: Any details about them — job, how you know them, personality
            birthday: Their birthday in YYYY-MM-DD format if mentioned
        """
        try:
            from backend.tools.relationship_tools import embed_text
            db = get_supabase()

            circle = "inner" if relationship_type in ["family", "friend"] else "community"
            person_data = {
                "user_id": self._user_id,
                "name": name,
                "relationship_type": relationship_type,
                "circle": circle,
                "tags": [],
            }
            if birthday:
                person_data["birthday"] = birthday

            res = db.table("people").insert(person_data).execute()
            person = res.data[0] if res.data else {}
            person_id = person.get("id")

            if notes and person_id:
                embedding = await embed_text(notes)
                note_row = {
                    "user_id": self._user_id,
                    "person_id": person_id,
                    "content": notes,
                    "source": "chat_extraction",
                }
                if embedding:
                    note_row["embedding"] = embedding
                db.table("relationship_notes").insert(note_row).execute()

            logger.info(f"[livekit] Added person: {name}")
            return f"Got it, I've added {name} to your people."
        except Exception as e:
            logger.error(f"[livekit] add_person error: {e}")
            return f"I had trouble adding {name}. Please try again."

    @function_tool
    async def remember_about_person(
        self,
        context: RunContext,
        person_name: str,
        note: str,
    ) -> str:
        """
        Save a note or memory about someone the user knows.
        Call this when the user shares information about a person:
        'Cherry got a new job', 'Vincent is moving to Abuja',
        'remember that Malik likes football'.

        Args:
            person_name: The name of the person
            note: The information to remember about them
        """
        try:
            from backend.tools.relationship_tools import embed_text
            db = get_supabase()

            res = db.table("people")\
                .select("id, name")\
                .eq("user_id", self._user_id)\
                .ilike("name", f"%{person_name}%")\
                .limit(1)\
                .execute()

            if not res.data:
                return f"I don't have {person_name} in your people yet. Want me to add them first?"

            person_id = res.data[0]["id"]
            embedding = await embed_text(note)
            note_row = {
                "user_id": self._user_id,
                "person_id": person_id,
                "content": note,
                "source": "chat_extraction",
            }
            if embedding:
                note_row["embedding"] = embedding
            db.table("relationship_notes").insert(note_row).execute()

            return f"Noted — I'll remember that about {person_name}."
        except Exception as e:
            return f"Couldn't save that note: {e}"

    @function_tool
    async def recall_person(self, context: RunContext, person_name: str) -> str:
        """
        Recall everything known about a person from relationship memory.
        Call this when the user asks about someone:
        'what do you know about Cherry?', 'tell me about Vincent',
        'who is Malik?'.

        Args:
            person_name: The name of the person to look up
        """
        try:
            db = get_supabase()

            person_res = db.table("people")\
                .select("*")\
                .eq("user_id", self._user_id)\
                .ilike("name", f"%{person_name}%")\
                .limit(1)\
                .execute()

            if not person_res.data:
                return f"I don't have anyone called {person_name} in your network."

            p = person_res.data[0]
            person_id = p["id"]

            notes_res = db.table("relationship_notes")\
                .select("content")\
                .eq("person_id", person_id)\
                .order("created_at", desc=True)\
                .limit(3)\
                .execute()

            notes = [n["content"] for n in (notes_res.data or [])]

            summary = f"{p['name']} is your {p['relationship_type']}."
            if p.get("birthday"):
                summary += f" Birthday: {p['birthday']}."
            if notes:
                summary += f" Notes: {' '.join(notes[:2])}"

            return summary
        except Exception as e:
            return f"Couldn't recall {person_name}: {e}"

    @function_tool
    async def add_goal(self, context: RunContext, title: str, urgency: str = "medium") -> str:
        """
        Add a new goal for the user.
        Call this when the user says 'add a goal', 'I want to achieve X',
        'set a goal to X'.

        Args:
            title: The goal description
            urgency: low, medium, or high
        """
        try:
            from datetime import datetime, timezone
            db = get_supabase()
            db.table("goals").insert({
                "user_id": self._user_id,
                "title": title,
                "urgency": urgency,
                "status": "active",
                "last_touched_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            return f"Goal added: {title}."
        except Exception as e:
            return f"Couldn't add that goal: {e}"

    @function_tool
    async def send_to_nudge_panel(
        self,
        context: RunContext,
        message: str,
        priority: str = "medium",
    ) -> str:
        """
        Add an item to the user's nudge panel for them to see later.
        Call this when the user says 'add this to my nudges',
        'remind me in the app', 'put this in my panel'.

        Args:
            message: The nudge message to display
            priority: low, medium, or high
        """
        try:
            from datetime import datetime, timezone
            db = get_supabase()
            db.table("nudge_history").insert({
                "user_id": self._user_id,
                "nudge_type": "general",
                "message": message,
                "priority": priority,
                "delivered_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            return "Added to your nudge panel."
        except Exception as e:
            return f"Couldn't add nudge: {e}"

    @function_tool
    async def find_nearby_places(
        self,
        context: RunContext,
        query: str,
        radius: int = 3000,
    ) -> str:
        """
        Find any nearby place using real Lagos data.
        Call when user asks to find any place near them:
        'find a restaurant', 'is there an ATM near me?',
        'where's the nearest pharmacy?', 'find a suya spot'.

        Args:
            query: What to find e.g. "restaurant", "church", "pharmacy", "ATM", "suya"
            radius: Search radius in meters (default 3000)
        """
        try:
            from backend.tools.maps_tools import find_nearby_places as _find
            results = await _find.__wrapped__(self._user_id, query, radius)

            if not results or (len(results) == 1 and "error" in results[0]):
                return f"I couldn't find any {query} nearby right now."

            parts = []
            for place in results[:3]:
                name = place.get("name", "Unknown")
                dist = place.get("distance_str", "")
                parts.append(f"{name}, {dist} away")

            return f"Here are some nearby {query}s: {'. '.join(parts)}."
        except Exception as e:
            return f"Couldn't search nearby places: {e}"

    @function_tool
    async def get_directions(
        self,
        context: RunContext,
        destination: str,
    ) -> str:
        """
        Get real traffic-aware travel time to a destination.
        Call when user asks how long to get somewhere or for directions:
        'how long to get to work?', 'how do I get home?',
        'directions to Blenco', 'travel time to the island'.

        Args:
            destination: Destination name e.g. "work", "home", "Ikeja City Mall"
        """
        try:
            from backend.tools.maps_tools import get_route_and_traffic as _route
            from backend.tools.maps_tools import search_place_by_name as _search

            db = get_supabase()
            dest_lat = dest_lng = None
            dest_label = destination

            # Resolve home/work from saved profile coords
            profile = db.table("users")\
                .select("home_lat,home_lng,work_lat,work_lng,home_address,work_address")\
                .eq("id", self._user_id)\
                .maybe_single()\
                .execute()

            if profile.data:
                d = destination.lower()
                if any(w in d for w in ["home", "house"]):
                    dest_lat = profile.data.get("home_lat")
                    dest_lng = profile.data.get("home_lng")
                    dest_label = profile.data.get("home_address") or "Home"
                elif any(w in d for w in ["work", "office", "job"]):
                    dest_lat = profile.data.get("work_lat")
                    dest_lng = profile.data.get("work_lng")
                    dest_label = profile.data.get("work_address") or "Work"

            # Geocode named place if no saved coords matched
            if not dest_lat or not dest_lng:
                place = await _search.__wrapped__(self._user_id, destination)
                if "error" not in place:
                    dest_lat = place.get("lat")
                    dest_lng = place.get("lng")
                    dest_label = place.get("name", destination)

            if not dest_lat or not dest_lng:
                return f"I couldn't find {destination} on the map."

            result = await _route.__wrapped__(self._user_id, dest_lat, dest_lng, dest_label)

            if "error" in result:
                return f"I couldn't get directions to {dest_label} right now."

            minutes = result.get("duration_minutes", 0)
            km = result.get("distance_km", 0)
            delay = result.get("traffic_delay_minutes", 0)

            if delay > 10:
                return (f"About {minutes} minutes to {dest_label}, {km} km. "
                        f"Heavy traffic with a {delay}-minute delay — consider leaving later.")
            elif delay > 3:
                return f"About {minutes} minutes to {dest_label}, {km} km, with some traffic."
            else:
                return f"About {minutes} minutes to {dest_label}, {km} km. Roads are clear."
        except Exception as e:
            return f"Couldn't get directions: {e}"

    @function_tool
    async def check_traffic(
        self,
        context: RunContext,
        destination: str = "work",
    ) -> str:
        """
        Check current traffic conditions to home or work.
        Call when user asks about traffic or whether to leave:
        'how's traffic?', 'should I leave now?', 'is there traffic to work?',
        'how long to get home?'.

        Args:
            destination: "home" or "work"
        """
        try:
            from backend.tools.maps_tools import check_traffic_to_saved_location as _traffic
            result = await _traffic.__wrapped__(self._user_id, destination)

            if "error" in result:
                return result["error"]

            return result.get("advice") or f"About {result.get('duration_minutes', '?')} minutes to {destination} right now."
        except Exception as e:
            return f"Couldn't check traffic: {e}"

    @function_tool
    async def update_goal(self, context: RunContext, goal_title: str, action: str) -> str:
        """
        Update, complete, or mark progress on an existing goal.
        Call this when user says 'I completed X', 'mark X as done',
        'I made progress on X', 'delete goal X'.

        Args:
            goal_title: The title or part of the title of the goal
            action: complete, touch (mark worked on), or delete
        """
        try:
            from datetime import datetime, timezone
            db = get_supabase()
            now = datetime.now(timezone.utc).isoformat()

            res = db.table("goals")\
                .select("id, title")\
                .eq("user_id", self._user_id)\
                .ilike("title", f"%{goal_title}%")\
                .limit(1)\
                .execute()

            if not res.data:
                return f"I couldn't find a goal matching '{goal_title}'."

            goal = res.data[0]
            goal_id = goal["id"]

            if action == "complete":
                db.table("goals").update({
                    "status": "completed",
                    "completed_at": now,
                }).eq("id", goal_id).execute()
                return f"Marked '{goal['title']}' as complete. Well done!"
            elif action == "delete":
                db.table("goals").delete().eq("id", goal_id).execute()
                return f"Deleted goal: {goal['title']}."
            else:
                db.table("goals").update({
                    "last_touched_at": now,
                }).eq("id", goal_id).execute()
                return f"Noted progress on '{goal['title']}'."
        except Exception as e:
            return f"Couldn't update goal: {e}"

    @function_tool
    async def list_people(self, context: RunContext) -> str:
        """
        List all people in the user's relationship network.
        Call this when user asks 'who are my people?',
        'who do I have saved?', 'list my contacts'.
        """
        try:
            db = get_supabase()
            res = db.table("people")\
                .select("name, relationship_type")\
                .eq("user_id", self._user_id)\
                .order("created_at")\
                .execute()

            people = res.data or []
            if not people:
                return "You don't have anyone in your people network yet."

            names = [f"{p['name']} ({p['relationship_type']})" for p in people[:5]]
            total = len(people)
            result = f"You have {total} people: {', '.join(names)}"
            if total > 5:
                result += f" and {total - 5} more."
            return result
        except Exception as e:
            return f"Couldn't get your people: {e}"


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
        stt=openai.STT(
            model="whisper-1",
            language="en",
            prompt="JARVIS",
        ),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(
            voice="alloy",
            speed=1.1,
        ),
    )

    agent = JARVISAgent(user_id=user_id, user_context=user_context)

    await session.start(
        room=ctx.room,
        agent=agent,
    )

    await session.generate_reply(
        instructions="Say hello to the user by name in one short sentence."
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
