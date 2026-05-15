"""
JARVIS Merge Thinking Pipeline v2 – Enhanced with Memory & Token Management
Improvements over v1:
- Token-aware context management
- Retrieves past merge sessions from memory
- Multi-turn merge conversations
- Pattern learning across decisions
- Handles multiple pending questions per user
"""

import json
from pathlib import Path
from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime

STATE_FILE = Path("/app/backend/data/jarvis_merge_state.json")
MERGE_HISTORY_FILE = Path("/app/backend/data/jarvis_merge_history.json")


class Pipeline:
    class Valves(BaseModel):
        merge_trigger_words: str = (
            "how should,how do I,how would you,best way,should I,"
            "what's the best,decide,decision,which option,what approach,"
            "recommend,advice on,help me choose"
        )
        ask_user_first: bool = True
        max_context_tokens: int = 100000  # Conservative limit for context window
        enable_pattern_learning: bool = True
        max_merge_history: int = 50  # Keep last N merge sessions

    def __init__(self):
        self.name = "JARVIS Merge Thinking v2 (Enhanced)"
        self.valves = self.Valves()
        self._ensure_files()

    def _ensure_files(self):
        """Initialize state and history files"""
        try:
            for file in [STATE_FILE, MERGE_HISTORY_FILE]:
                if not file.exists():
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text(json.dumps({} if file == STATE_FILE else []))
        except Exception:
            pass

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

    def _load_history(self) -> List[Dict]:
        """Load past merge sessions for pattern learning"""
        try:
            history = json.loads(MERGE_HISTORY_FILE.read_text())
            return history[-self.valves.max_merge_history:]
        except Exception:
            return []

    def _save_merge_to_history(self, user_id: str, question: str, user_approach: str):
        """Save completed merge for future pattern learning"""
        try:
            history = self._load_history()
            history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "question": question,
                "user_approach": user_approach,
            })
            # Keep only recent history
            history = history[-self.valves.max_merge_history:]
            MERGE_HISTORY_FILE.write_text(json.dumps(history, indent=2))
        except Exception:
            pass

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 chars for English)"""
        return len(text) // 4

    def _get_conversation_tokens(self, messages: List[Dict]) -> int:
        """Estimate total tokens in conversation"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self._estimate_tokens(content)
        return total

    def _get_relevant_patterns(self, current_question: str, user_id: str) -> str:
        """Retrieve similar past decisions for pattern learning"""
        if not self.valves.enable_pattern_learning:
            return ""

        history = self._load_history()
        user_history = [h for h in history if h.get("user_id") == user_id]
        
        if not user_history:
            return ""

        # Simple relevance: last 3 decisions (could be improved with embeddings)
        recent = user_history[-3:]
        
        patterns = "\n[PAST DECISION PATTERNS]\n"
        for i, session in enumerate(recent, 1):
            patterns += f"{i}. Question: {session.get('question', 'N/A')}\n"
            patterns += f"   Your approach: {session.get('user_approach', 'N/A')}\n"
        
        patterns += "\nUse these to identify patterns in the user's decision-making style.\n"
        return patterns

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
        merge_session_key = f"{user_id}_merge_session"

        # === TOKEN MANAGEMENT CHECK ===
        total_tokens = self._get_conversation_tokens(messages)
        if total_tokens > self.valves.max_context_tokens:
            # Inject warning to LLM to summarize conversation
            body["messages"].insert(0, {
                "role": "system",
                "content": (
                    f"[TOKEN WARNING] Conversation is at {total_tokens} tokens "
                    f"(limit: {self.valves.max_context_tokens}). "
                    "Summarize key points and suggest starting a new conversation."
                ),
            })

        # === VERIFY MODE (manual) ===
        if user_text.strip().lower().startswith(("verify:", "verify this")):
            body["messages"].insert(0, {
                "role": "system",
                "content": (
                    "This is a VERIFY request. Use tools to double-check facts. "
                    "If multiple models are available, compare responses. "
                    "Show sources and confidence level."
                ),
            })
            return body

        # === MULTI-TURN MERGE: User wants to iterate on merge ===
        if merge_session_key in state and user_text.lower().startswith(("what if", "but what about", "how about")):
            original_q = state[merge_session_key].get("question", "")
            original_approach = state[merge_session_key].get("user_approach", "")
            
            body["messages"].insert(-1, {
                "role": "system",
                "content": (
                    f"[MERGE ITERATION] Original question: {original_q}\n"
                    f"Original approach: {original_approach}\n"
                    f"User is now asking: {user_text}\n\n"
                    "Re-analyze with this new constraint/question. "
                    "Show how it changes your recommendation."
                ),
            })
            return body

        # === USER JUST ANSWERED "How would YOU handle this?" ===
        if awaiting_key in state:
            original_q = state.pop(awaiting_key)
            
            # Save to history for pattern learning
            self._save_merge_to_history(user_id, original_q, user_text)
            
            # Start merge session (allows multi-turn)
            state[merge_session_key] = {
                "question": original_q,
                "user_approach": user_text,
                "started_at": datetime.utcnow().isoformat()
            }
            self._save_state(state)

            # Get relevant past patterns
            patterns = self._get_relevant_patterns(original_q, user_id)

            merge_instruction = {
                "role": "system",
                "content": (
                    f"[MERGE THINKING] Original question: {original_q}\n"
                    f"User's approach: {user_text}\n"
                    f"{patterns}\n"
                    "Instructions:\n"
                    "1. Research the question independently using tools if available.\n"
                    "2. Present your merged analysis:\n"
                    "   - Where you and the user ALIGN (and why it's strong)\n"
                    "   - Where you DISAGREE (and exactly why, with evidence)\n"
                    "   - Your final recommended action\n"
                    "3. Be direct and honest. Never be diplomatic at the expense of truth.\n"
                    "4. If you see patterns from past decisions, mention them."
                ),
            }
            body["messages"].insert(-1, merge_instruction)
            return body

        # === END MERGE SESSION: User says "thanks" or moves to new topic ===
        if merge_session_key in state:
            end_phrases = ["thanks", "got it", "okay", "ok", "new topic", "different question"]
            if any(phrase in user_text.lower() for phrase in end_phrases):
                state.pop(merge_session_key, None)
                self._save_state(state)

        # === DETECT NEW DECISION QUESTION ===
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

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """
        Post-process LLM response (currently unused, but available for:
        - Injecting memory updates
        - Adding follow-up suggestions
        - Cost tracking
        """
        return body
