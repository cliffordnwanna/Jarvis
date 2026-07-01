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


JARVIS_VOICE_PROMPT = """You are JARVIS, a proactive personal AI assistant in voice mode.

VOICE RULES — strictly follow these:
- Maximum 2 short sentences per response
- Never say markdown, bullets, or lists
- Speak naturally like a smart friend
- Use the user's name occasionally to feel personal
- Be warm, direct, and confident

USER CONTEXT:
{user_context}

IMPORTANT — you know this person well from the context above.
When asked about their sister, people, home, work — answer from context first before calling any tool.
Only call tools when you need live data (weather, traffic, places, exchange rates, web search).
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
        Find any nearby place — restaurant, church, ATM, pharmacy,
        hotel, mechanic, suya spot, filling station, anything.
        Call this when user asks to find any place near them.

        Args:
            query: What to find e.g. "restaurant", "church", "ATM"
            radius: Search radius in meters, default 3000
        """
        api_key = os.getenv("TOMTOM_API_KEY")
        if not api_key:
            return "Location search is not configured."

        ws = await cache_get(self._user_id)
        if not ws:
            return "I don't have your location yet."

        location = ws.get("location", {})
        lat = location.get("lat") or ws.get("_meta", {}).get("lat")
        lng = location.get("lng") or ws.get("_meta", {}).get("lng")
        if not lat or not lng:
            return "I can't get your location right now."

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"https://api.tomtom.com/search/2/poiSearch/{query}.json",
                    params={
                        "key": api_key,
                        "lat": lat,
                        "lon": lng,
                        "radius": radius,
                        "limit": 4,
                        "language": "en-GB",
                        "countrySet": "NG",
                    },
                    timeout=10.0,
                )
                data = r.json()

            results = [item for item in data.get("results", [])
                       if item.get("poi", {}).get("name")][:3]

            if not results:
                r2 = await client.get(
                    f"https://api.tomtom.com/search/2/search/{query}.json",
                    params={
                        "key": api_key,
                        "lat": lat,
                        "lon": lng,
                        "radius": radius,
                        "limit": 3,
                        "countrySet": "NG",
                    },
                    timeout=10.0,
                )
                results = r2.json().get("results", [])[:3]

            if not results:
                return f"I couldn't find any {query} nearby right now."

            parts = []
            for place in results:
                name = place.get("poi", {}).get("name") or \
                       place.get("address", {}).get("freeformAddress", "Unknown")
                dist = place.get("dist", 0)
                dist_str = f"{round(dist / 1000, 1)} km" if dist > 1000 else f"{int(dist)} metres"
                parts.append(f"{name}, {dist_str} away")

            return f"Nearby {query}s: {'. '.join(parts)}."

        except Exception as e:
            logger.error(f"[voice] find_nearby_places error: {e}")
            return f"I had trouble searching for {query} nearby."

    @function_tool
    async def get_directions(
        self,
        context: RunContext,
        destination: str,
    ) -> str:
        """
        Get travel time and directions with real traffic data.
        Call when user asks how long to get somewhere or for directions.
        Automatically resolves home and work from saved addresses.

        Args:
            destination: Where to go e.g. "work", "home", "Ikeja",
                         "Duchess Hospital", "Marina"
        """
        api_key = os.getenv("TOMTOM_API_KEY")
        if not api_key:
            return "Directions are not configured right now."

        ws = await cache_get(self._user_id)
        if not ws:
            return "I don't have your location yet."

        location = ws.get("location", {})
        origin_lat = location.get("lat") or ws.get("_meta", {}).get("lat")
        origin_lng = location.get("lng") or ws.get("_meta", {}).get("lng")
        if not origin_lat:
            return "I can't get your current location."

        dest_lat = dest_lng = dest_label = None
        dest_lower = destination.lower().strip()

        if any(w in dest_lower for w in ["home", "house", "back home"]):
            p = get_supabase().table("users")\
                .select("home_lat,home_lng,home_address")\
                .eq("id", self._user_id).maybe_single().execute()
            if p.data and p.data.get("home_lat"):
                dest_lat, dest_lng = p.data["home_lat"], p.data["home_lng"]
                dest_label = p.data.get("home_address", "Home")
            else:
                return "You haven't set a home address yet. Tell me your home address to save it."

        elif any(w in dest_lower for w in ["work", "office", "job"]):
            p = get_supabase().table("users")\
                .select("work_lat,work_lng,work_address")\
                .eq("id", self._user_id).maybe_single().execute()
            if p.data and p.data.get("work_lat"):
                dest_lat, dest_lng = p.data["work_lat"], p.data["work_lng"]
                dest_label = p.data.get("work_address", "Work")
            else:
                return "You haven't set a work address yet. Tell me your work address to save it."

        else:
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.get(
                        f"https://api.tomtom.com/search/2/search/{destination} Lagos.json",
                        params={
                            "key": api_key,
                            "limit": 1,
                            "countrySet": "NG",
                            "lat": origin_lat,
                            "lon": origin_lng,
                        },
                        timeout=8.0,
                    )
                    data = r.json()
                results = data.get("results", [])
                if not results:
                    return f"I couldn't find {destination} on the map."
                pos = results[0].get("position", {})
                dest_lat = pos.get("lat")
                dest_lng = pos.get("lon")
                dest_label = results[0].get("poi", {}).get("name") or \
                             results[0].get("address", {}).get("freeformAddress", destination)
            except Exception:
                return f"I couldn't locate {destination}."

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"https://api.tomtom.com/routing/1/calculateRoute/"
                    f"{origin_lat},{origin_lng}:{dest_lat},{dest_lng}/json",
                    params={
                        "key": api_key,
                        "travelMode": "car",
                        "traffic": "true",
                        "routeType": "fastest",
                        "computeTravelTimeFor": "all",
                    },
                    timeout=12.0,
                )
                data = r.json()

            routes = data.get("routes", [])
            if not routes:
                return f"I couldn't find a route to {dest_label}."

            summary = routes[0].get("summary", {})
            minutes = int(summary.get("travelTimeInSeconds", 0) / 60)
            no_traffic_min = int(summary.get("noTrafficTravelTimeInSeconds", 0) / 60)
            km = round(summary.get("lengthInMeters", 0) / 1000, 1)
            delay = minutes - no_traffic_min

            if delay > 15:
                return (f"It'll take about {minutes} minutes to {dest_label} — "
                        f"heavy traffic adding {delay} minutes. "
                        f"Only {no_traffic_min} minutes without traffic.")
            elif delay > 5:
                return f"About {minutes} minutes to {dest_label}, {km} kilometres, with some traffic."
            else:
                return f"About {minutes} minutes to {dest_label}, {km} kilometres. Roads look clear."

        except Exception as e:
            logger.error(f"[voice] get_directions error: {e}")
            return "I had trouble getting directions right now."

    @function_tool
    async def check_traffic(
        self,
        context: RunContext,
        destination: str = "work",
    ) -> str:
        """
        Check current traffic conditions to home or work.
        Call when user asks about traffic, whether to leave,
        how bad the roads are, or if it is a good time to go.

        Args:
            destination: "home" or "work"
        """
        return await self.get_directions(context, destination)

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
    """Build rich user context for voice agent system prompt."""
    from datetime import datetime
    import pytz

    db = get_supabase()
    parts = []

    # 1. User profile — name, home, work
    try:
        profile = db.table("users")\
            .select("display_name,home_lat,home_lng,home_address,work_lat,work_lng,work_address")\
            .eq("id", user_id)\
            .maybe_single()\
            .execute()

        if profile.data:
            name = profile.data.get("display_name", "")
            if name:
                parts.append(f"The user's name is {name}.")

            home_addr = profile.data.get("home_address", "")
            home_lat = profile.data.get("home_lat")
            home_lng = profile.data.get("home_lng")
            if home_lat and home_lng:
                parts.append(
                    f"Home: {home_addr} (coordinates: {home_lat}, {home_lng}). "
                    f"Use these coords when asked for directions home."
                )

            work_addr = profile.data.get("work_address", "")
            work_lat = profile.data.get("work_lat")
            work_lng = profile.data.get("work_lng")
            if work_lat and work_lng:
                parts.append(
                    f"Work: {work_addr} (coordinates: {work_lat}, {work_lng}). "
                    f"Use these coords when asked for directions to work."
                )
    except Exception as e:
        logger.warning(f"[voice] profile fetch error: {e}")

    # 2. Current location and weather from world state
    try:
        ws = await cache_get(user_id)
        if ws:
            location = ws.get("location", {})
            city = location.get("city", "")
            district = location.get("district", "")
            loc_str = f"{district}, {city}" if district else city
            if loc_str.strip():
                parts.append(f"Current location: {loc_str}, Nigeria.")

            weather = ws.get("environment", {}).get("weather", {})
            temp = weather.get("temp_c")
            condition = weather.get("description", weather.get("condition", ""))
            if temp:
                parts.append(f"Current weather: {temp}°C, {condition}.")
    except Exception as e:
        logger.warning(f"[voice] world state fetch error: {e}")

    # 3. Current time in Lagos
    try:
        lagos_tz = pytz.timezone("Africa/Lagos")
        now = datetime.now(lagos_tz)
        parts.append(
            f"Current time: {now.strftime('%I:%M %p')} on "
            f"{now.strftime('%A, %B %d, %Y')}."
        )
    except Exception:
        pass

    # 4. Active goals
    try:
        goals = db.table("goals")\
            .select("title")\
            .eq("user_id", user_id)\
            .eq("status", "active")\
            .execute()
        if goals.data:
            titles = [g["title"] for g in goals.data[:3]]
            parts.append(f"Active goals: {', '.join(titles)}.")
    except Exception as e:
        logger.warning(f"[voice] goals fetch error: {e}")

    # 5. People in network
    try:
        people = db.table("people")\
            .select("name, relationship_type")\
            .eq("user_id", user_id)\
            .execute()
        if people.data:
            people_list = [
                f"{p['name']} ({p['relationship_type']})"
                for p in people.data[:5]
            ]
            parts.append(
                f"People in network: {', '.join(people_list)}. "
                f"Use recall_person to get details about any of them."
            )
    except Exception as e:
        logger.warning(f"[voice] people fetch error: {e}")

    # 6. Upcoming reminders today
    try:
        lagos_tz = pytz.timezone("Africa/Lagos")
        today = datetime.now(lagos_tz).strftime("%Y-%m-%d")
        reminders = db.table("relationship_events")\
            .select("title, scheduled_at")\
            .eq("user_id", user_id)\
            .eq("nudge_sent", False)\
            .gte("scheduled_at", today)\
            .lte("scheduled_at", today + "T23:59:59")\
            .execute()
        if reminders.data:
            r_list = [r["title"] for r in reminders.data[:3]]
            parts.append(f"Reminders today: {', '.join(r_list)}.")
    except Exception as e:
        logger.warning(f"[voice] reminders fetch error: {e}")

    return "\n".join(parts)


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
