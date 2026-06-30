"""
JARVIS LiveKit Voice Agent
Runs as a separate process alongside the FastAPI backend.
Handles real-time voice: STT (OpenAI Whisper) → LangGraph tools → TTS (OpenAI)
"""
import asyncio
import os
import logging
from dotenv import load_dotenv
load_dotenv()

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import openai, silero

from backend.tools.world_tools import get_world_state, send_nudge, get_nearby_places, get_travel_eta
from backend.tools.goal_tools import get_goals, manage_goal
from backend.tools.relationship_tools import hybrid_search_notes_tool, add_person, add_note_for_person, create_reminder
from backend.tools.search_tools import web_search, get_exchange_rate, calculate
from backend.db.postgres import get_supabase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def get_user_context(user_id: str) -> str:
    """Fetch user profile and world state for system prompt injection."""
    db = get_supabase()
    context_parts = []

    try:
        profile = db.table("users")\
            .select("display_name, timezone")\
            .eq("id", user_id)\
            .maybe_single()\
            .execute()
        if profile.data and profile.data.get("display_name"):
            context_parts.append(f"User's name: {profile.data['display_name']}")
    except Exception:
        pass

    try:
        ws = db.table("world_state")\
            .select("state")\
            .eq("user_id", user_id)\
            .maybe_single()\
            .execute()
        if ws and ws.data and ws.data.get("state"):
            state = ws.data["state"]
            temporal = state.get("temporal", {})
            location = state.get("location", {})
            weather = state.get("environment", {}).get("weather", {})

            district = location.get("district", "")
            city = location.get("city", "")
            loc_str = f"{district}, {city}" if district and district != city else city

            context_parts.append(f"Current time: {temporal.get('timestamp', 'unknown')}")
            context_parts.append(f"Location: {loc_str}, {location.get('country', '')}")
            context_parts.append(f"Weather: {weather.get('temp_c')}°C, {weather.get('description', '')}")
    except Exception:
        pass

    return "\n".join(context_parts)


JARVIS_VOICE_PROMPT = """You are JARVIS — a proactive personal AI assistant.
You are in voice mode. Keep all responses SHORT — 1-3 sentences maximum.
Never use markdown, bullet points, or formatting — speak naturally.
Do not say "As an AI" or hedge unnecessarily.
Be warm, direct, and genuinely helpful.

You have access to tools: search the web, check weather, manage goals,
remember people, set reminders, calculate, get exchange rates.

{user_context}
"""


class JARVISAgent(Agent):
    def __init__(self, user_id: str, user_context: str):
        self.user_id = user_id
        system_prompt = JARVIS_VOICE_PROMPT.format(user_context=user_context)
        super().__init__(
            instructions=system_prompt,
            tools=[
                get_world_state,
                send_nudge,
                get_goals,
                manage_goal,
                web_search,
                get_exchange_rate,
                calculate,
                hybrid_search_notes_tool,
                add_person,
                add_note_for_person,
                get_nearby_places,
                get_travel_eta,
                create_reminder,
            ]
        )


async def entrypoint(ctx: agents.JobContext):
    """LiveKit agent entrypoint — called for each room connection."""
    await ctx.connect()

    # Room name format: jarvis-{user_id}
    room_name = ctx.room.name
    user_id = room_name.removeprefix("jarvis-") if room_name.startswith("jarvis-") else ""

    logger.info(f"[livekit] Agent connected to room: {room_name}, user: {user_id}")

    user_context = await get_user_context(user_id) if user_id else ""

    session = AgentSession(
        stt=openai.STT(model="whisper-1"),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(voice="alloy"),
        vad=silero.VAD.load(),
    )

    jarvis = JARVISAgent(user_id=user_id, user_context=user_context)

    await session.start(
        room=ctx.room,
        agent=jarvis,
        room_input_options=RoomInputOptions(
            noise_cancellation=openai.realtime.NoiseReduction(type="near_field"),
        ),
    )

    await session.generate_reply(
        instructions="Greet the user briefly and ask how you can help. Keep it to one sentence."
    )


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint)
    )
