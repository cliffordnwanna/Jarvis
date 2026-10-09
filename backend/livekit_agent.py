"""
JARVIS LiveKit Voice Agent.

Reverted from a Pipecat-based rewrite back to the LiveKit Agents SDK
(the architecture this file already used before Phase 6 started): LiveKit
Agents already provides automatic worker dispatch, VAD, interruption
handling, and a tool-calling agent session -- Pipecat added no capability
this SDK lacks for this use case, and its LiveKit integration in the
installed version (confirmed by direct inspection) has no automatic job
dispatch, which would have required spawning a worker process per session
from FastAPI -- unnecessary process-management complexity avoided by
staying on this SDK.

What changed from the pre-Phase-6 version of this file (confirmed by
reading that version in full before rewriting):
  - stt: openai.STT("whisper-1") [batch] -> deepgram.STT (streaming,
    interim_results=True by default, model="nova-3" by default -- both
    confirmed via inspect.signature(deepgram.STT.__init__))
  - llm: gpt-4o-mini (unchanged model choice, kept per explicit cost
    instruction to use gpt-4o-mini everywhere rather than gpt-4o)
  - vad: none -> silero.VAD.load() passed to AgentSession(vad=...) --
    confirmed via inspect.signature(AgentSession.__init__) that vad,
    allow_interruptions, min_interruption_duration, and
    min_interruption_words are all real, directly supported parameters;
    the previous file simply never passed vad= at all.
  - tools: 15 independently-reimplemented @function_tool methods on
    JARVISAgent, duplicating (and drifted from) backend/tools/* ->
    backend/voice/tool_adapter.py wraps the SAME tool objects backend/
    agent.py uses. One registry, two calling conventions.
  - memory: zero access to Mem0/memory_files -> backend/voice/context.py
    builds the same BASE_SYSTEM_PROMPT + memory index + Mem0 recall text
    comment.py's.
  - conversation identity: voice was invisible to the conversations/
    messages tables -> every turn is persisted through backend/voice/
    conversation.py, the same tables and insert shape as text chat.

cli.run_app(WorkerOptions(...)) is kept as the startup mechanism exactly
as it was -- confirmed still valid against livekit-agents==1.8.5 by
inspecting cli.run_app and WorkerOptions directly. The LiveKit docs
describe this as a legacy CLI path in favor of `lk agent ...`, but
migrating the startup mechanism is a deployment concern, not a Phase 6
voice-capability concern, per explicit instruction to not let that
derail this phase.
"""
import os
import logging
from dotenv import load_dotenv
load_dotenv()

from livekit import agents
from livekit.agents import AgentSession, Agent, JobContext, WorkerOptions, TurnHandlingOptions, cli
from livekit.agents.voice.turn import InterruptionOptions
from livekit.plugins import deepgram, openai, silero

from backend.db.postgres import get_supabase
from backend.db.cache import cache_get
from backend.voice.tool_adapter import get_voice_tools
from backend.voice.context import build_voice_system_prompt
from backend.voice.conversation import get_or_create_voice_conversation, persist_voice_turn

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def entrypoint(ctx: JobContext):
    try:
        await ctx.connect()

        room_name = ctx.room.name
        user_id = room_name.replace("jarvis-", "") if room_name.startswith("jarvis-") else ""

        # conversation_id arrives via the connecting PARTICIPANT's metadata,
        # not the room's. backend/routers/voice.py's AccessToken.with_metadata()
        # sets metadata on the token's identity -- LiveKit delivers that as
        # RemoteParticipant.metadata on join, never as ctx.room.metadata
        # (room metadata is a separate server-side property, never set here).
        # An earlier version of this read ctx.room.metadata directly, which
        # is always empty for a token-only join, silently falling back to
        # user_id as conversation_id every time -- confirmed by inspecting
        # real persisted rows after a voice session: all turns landed under
        # conversation_id=user_id instead of the text thread's conversation_id.
        conversation_id = user_id
        try:
            import json
            participant = await ctx.wait_for_participant()
            metadata = json.loads(participant.metadata) if participant.metadata else {}
            conversation_id = metadata.get("conversation_id") or user_id
            user_id = metadata.get("user_id") or user_id
        except Exception as e:
            logger.warning(f"[livekit] participant metadata parse failed, falling back to room name: {e}")

        logger.info(f"[livekit] Room: {room_name}, user: {user_id}, conversation: {conversation_id}")

        is_first_turn = await get_or_create_voice_conversation(conversation_id, user_id)
        logger.info(f"[livekit] conversation ready, first_turn={is_first_turn}")

        system_prompt = await build_voice_system_prompt(user_id)
        logger.info(f"[livekit] System prompt built: {len(system_prompt)} chars")

        tools = get_voice_tools(user_id)
        agent = Agent(instructions=system_prompt, tools=tools)

        session = AgentSession(
            stt=deepgram.STT(
                model="nova-3",
                language="multi",
                interim_results=True,
                # Confirmed via inspect.signature(deepgram.STT.__init__) and
                # by reading the plugin's stt.py: enable_diarization=True
                # makes Deepgram tag each transcribed word with a speaker
                # label, which the plugin reduces to one speaker_id per
                # utterance (majority vote across words) and which flows
                # through to UserInputTranscribedEvent.speaker_id (confirmed
                # via grep of livekit.agents.voice.agent_activity/events).
                # Enabled here only to capture and log that label -- JARVIS
                # does not yet change behavior based on it (e.g. does not
                # announce a second speaker), since this is a single-user
                # assistant today, not a meeting transcriber.
                enable_diarization=True,
                api_key=os.getenv("DEEPGRAM_API_KEY"),
            ),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=openai.TTS(voice="alloy", speed=1.0),
            vad=silero.VAD.load(),
            # allow_interruptions=True is deprecated in this version
            # (confirmed by the deprecation warning it raises directly);
            # turn_handling=TurnHandlingOptions(interruption=...) is the
            # real, current replacement, confirmed via the TypedDict's own
            # __annotations__.
            turn_handling=TurnHandlingOptions(
                interruption=InterruptionOptions(enabled=True, mode="vad"),
            ),
        )

        # Logs the speaker_id Deepgram's diarization attaches to each final
        # transcript, when present. Log-only for now, per explicit scope --
        # does not affect persistence or agent behavior. Confirmed real via
        # UserInputTranscribedEvent.speaker_id (livekit.agents.voice.events).
        @session.on("user_input_transcribed")
        def _on_user_input_transcribed(event):
            if event.is_final and event.speaker_id:
                logger.info(f"[livekit] speaker_id={event.speaker_id} transcript={event.transcript!r}")

        # Confirmed via direct source inspection (grepped AgentSession's own
        # .emit() calls) that the real event is "conversation_item_added"
        # with a ConversationItemAddedEvent(item=ChatMessage) payload --
        # not "user_speech_committed"/"agent_speech_committed", which don't
        # exist on this SDK version. item.role is one of
        # developer/system/user/assistant; item.text_content gives the
        # plain string (content itself is list[ChatContent], not str).
        import asyncio

        @session.on("conversation_item_added")
        def _on_conversation_item(event):
            item = event.item
            if not hasattr(item, "role") or item.role not in ("user", "assistant"):
                return
            text = item.text_content
            if text:
                asyncio.create_task(persist_voice_turn(conversation_id, user_id, item.role, text))

        await session.start(room=ctx.room, agent=agent)
        logger.info("[livekit] Session started, generating greeting")

        await session.generate_reply(
            instructions="Greet the user by name warmly. One sentence only. Be brief."
        )
        logger.info("[livekit] Greeting generated")

    except Exception as e:
        logger.error(f"[livekit] Entrypoint crashed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
