"""
JARVIS Merge Thinking Pipeline – Persistent across restarts
Uses JSON file in Open WebUI data volume.

How it works:
1. User asks a decision question → JARVIS asks "How would YOU handle this?"
2. User answers → JARVIS merges both perspectives (honest, no diplomacy)
3. State survives container restarts via file-backed JSON storage

Verify mode:
  Type "verify:" or "verify this" before/after any answer to trigger
  fact-checking with tool use and cross-model comparison.
"""

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

STATE_FILE = Path("/app/backend/data/jarvis_merge_state.json")


class Pipeline:
    class Valves(BaseModel):
        merge_trigger_words: str = (
            "how should,how do I,how would you,best way,should I,"
            "what's the best,decide,decision,which option,what approach"
        )
        ask_user_first: bool = True

    def __init__(self):
        self.name = "JARVIS Merge Thinking (Persistent)"
        self.valves = self.Valves()
        self._ensure_state_file()

    def _ensure_state_file(self):
        try:
            if not STATE_FILE.exists():
                STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                STATE_FILE.write_text(json.dumps({}))
        except Exception:
            pass  # Graceful fallback if volume not mounted

    def _load_state(self) -> dict:
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}

    def _save_state(self, state: dict):
        try:
            STATE_FILE.write_text(json.dumps(state, indent=2))
        except Exception:
            pass

    def is_decision_question(self, message: str) -> bool:
        triggers = self.valves.merge_trigger_words.lower().split(",")
        return any(t.strip() in message.lower() for t in triggers)

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        messages = body.get("messages", [])
        if not messages:
            return body

        last_msg = messages[-1]
        user_text = (
            last_msg.get("content", "")
            if isinstance(last_msg.get("content"), str)
            else ""
        )
        user_id = user.get("id", "default") if user else "default"

        state = self._load_state()
        awaiting_key = f"{user_id}_awaiting"

        # === VERIFY MODE (manual) – check first so it works independently ===
        if user_text.strip().lower().startswith(("verify:", "verify this")):
            body["messages"].insert(0, {
                "role": "system",
                "content": (
                    "This is a VERIFY request. Use tools to double-check facts. "
                    "If multiple models are available, compare Claude and GPT-4o. "
                    "Show sources and confidence level."
                ),
            })
            return body

        # === USER JUST ANSWERED "How would YOU handle this?" ===
        if awaiting_key in state:
            original_q = state.pop(awaiting_key)
            self._save_state(state)

            merge_instruction = {
                "role": "system",
                "content": (
                    f"[MERGE THINKING] Original question: {original_q}\n"
                    f"User's approach: {user_text}\n\n"
                    "Instructions:\n"
                    "1. Research the question independently using tools if available.\n"
                    "2. Present your merged analysis:\n"
                    "   - Where you and the user ALIGN (and why it's strong)\n"
                    "   - Where you DISAGREE (and exactly why, with evidence)\n"
                    "   - Your final recommended action\n"
                    "3. Be direct and honest. Never be diplomatic at the expense of truth."
                ),
            }
            body["messages"].insert(-1, merge_instruction)
            return body

        # === DETECT DECISION QUESTION ===
        if (
            self.valves.ask_user_first
            and self.is_decision_question(user_text)
            and len(user_text) > 20
        ):
            state[awaiting_key] = user_text
            self._save_state(state)

            body["messages"][-1]["content"] = (
                f"The user asked: '{user_text}'\n\n"
                "Before answering, reply with ONLY this one question and nothing else:\n"
                "'How would YOU handle this?'"
            )

        return body
