# Merge Thinking Pipeline - Detailed Explanation & Comparison

## How It Works (Current v1)

### The Flow

```
1. USER: "How should I price my SaaS product?"
   ↓
2. PIPELINE: Detects trigger words ("how should") → Saves question to state
   ↓
3. JARVIS: "How would YOU handle this?"
   ↓
4. USER: "I'd charge $99/month based on competitors"
   ↓
5. PIPELINE: Detects awaiting state → Injects merge instruction
   ↓
6. JARVIS: [Uses tools to research] → Compares approaches → Merges honestly
```

### What Happens Behind the Scenes

**Step 1-2: Question Detection**
- Pipeline scans your message for trigger words
- If found + message >20 chars → saves to `jarvis_merge_state.json`
- Replaces your message with instruction to ask "How would YOU handle this?"

**Step 3-4: User Response**
- Your answer is captured as-is
- Pipeline checks if there's a pending question in state

**Step 5-6: Merge Execution**
- Pipeline injects a system message with:
  - Original question
  - Your approach
  - Instructions to research independently and merge
- LLM sees this context and responds with merged analysis

---

## Current Limitations (v1)

### 1. **No Token Management** ❌
**Problem:** Long conversations will hit context limits (128k tokens for GPT-4o)

**What happens:**
- Pipeline passes entire conversation history unchanged
- No tracking of token usage
- When you hit the limit, requests fail with cryptic errors

**Impact:** After ~50-100 messages, JARVIS stops working

---

### 2. **No Knowledge Retrieval** ❌
**Problem:** Doesn't access Open WebUI's memory or past merges

**What it CAN'T do:**
- "Remember how I handled pricing decisions before"
- Pull relevant documents you uploaded
- Learn patterns across multiple merge sessions

**Current behavior:** Each merge is isolated, no learning

---

### 3. **Primitive State Management** ❌
**Problem:** Only stores ONE pending question per user

**Example failure:**
```
YOU: "How should I price my product?"
JARVIS: "How would YOU handle this?"
YOU: "Wait, also how should I hire my first engineer?"
     ↑ This OVERWRITES the pricing question
YOU: "I'd charge $99/month"
     ↑ JARVIS thinks this is about hiring, not pricing
```

---

### 4. **No Multi-Turn Conversations** ❌
**Problem:** After merge completes, state is cleared

**What you CAN'T do:**
```
YOU: "How should I price my product?"
JARVIS: [Merge happens]
YOU: "What if I changed the pricing to $49?"
     ↑ Pipeline doesn't know this relates to previous merge
```

---

### 5. **Limited Context Injection** ❌
**Problem:** Merge instruction inserted at position -1 (before last message)

**Missing:**
- Past decision patterns
- Relevant uploaded documents
- User preferences from memory
- Previous merge outcomes

---

## v2 Improvements

| Feature | v1 | v2 |
|---------|----|----|
| **Token Management** | None | Tracks tokens, warns at 100k limit |
| **Pattern Learning** | No | Stores last 50 merges, retrieves similar ones |
| **Multi-Turn Merge** | No | Detects "what if" questions, continues merge |
| **State Management** | 1 question/user | Supports merge sessions + iterations |
| **History** | None | Persistent merge history in JSON |
| **Context Injection** | Basic | Includes past patterns + session context |

---

## How v2 Handles Your Concerns

### 1. Token Management
```python
total_tokens = self._get_conversation_tokens(messages)
if total_tokens > 100000:
    # Warns LLM to summarize and suggest new conversation
```

**Estimation:** ~4 chars = 1 token (conservative)

**What happens at limit:**
- Pipeline injects warning to LLM
- LLM summarizes key points
- Suggests starting fresh conversation
- You don't lose context, just get proactive warning

---

### 2. Knowledge Retrieval & Orchestration

**Pattern Learning:**
```python
def _get_relevant_patterns(self, current_question, user_id):
    # Retrieves last 3 similar decisions
    # Shows your past approaches
    # LLM identifies patterns in your decision-making
```

**Example output to LLM:**
```
[PAST DECISION PATTERNS]
1. Question: How should I price my consulting?
   Your approach: Started at $150/hr, raised to $200/hr after 3 months

2. Question: How should I hire my first employee?
   Your approach: Contract-to-hire, 3-month trial

Use these to identify patterns in the user's decision-making style.
```

**Limitations (still present):**
- Doesn't query Open WebUI's memory system (requires API integration)
- Doesn't search uploaded RAG documents (requires embeddings)
- Pattern matching is simple (last 3 decisions, not semantic search)

**Future improvement:** Add embeddings for semantic similarity

---

### 3. Multi-Turn Merge Sessions

**v2 tracks active merge sessions:**
```python
if user_text.startswith(("what if", "but what about", "how about")):
    # Continues merge with new constraint
    # Preserves original question + your approach
```

**Example:**
```
YOU: "How should I price my product?"
JARVIS: "How would YOU handle this?"
YOU: "I'd charge $99/month"
JARVIS: [Merge analysis]
YOU: "What if I offered a $49 tier?"
     ↑ v2 detects this, re-runs merge with new constraint
JARVIS: [Updated analysis comparing $99 vs $49+$99 tiers]
```

**Session ends when you say:** "thanks", "got it", "new topic"

---

### 4. Data Handling

**What the pipeline stores:**

**State file** (`jarvis_merge_state.json`):
```json
{
  "user123_awaiting": "How should I price my product?",
  "user123_merge_session": {
    "question": "How should I price my product?",
    "user_approach": "I'd charge $99/month",
    "started_at": "2026-02-21T12:00:00Z"
  }
}
```

**History file** (`jarvis_merge_history.json`):
```json
[
  {
    "timestamp": "2026-02-21T12:00:00Z",
    "user_id": "user123",
    "question": "How should I price my product?",
    "user_approach": "I'd charge $99/month"
  }
]
```

**Size limits:**
- State file: ~1-5 KB (only active sessions)
- History file: ~50 KB (last 50 merges)
- Both survive container restarts (stored in Open WebUI volume)

**Privacy:** All stored locally in your deployment, never sent to external services

---

## Token Budget Breakdown

**Typical merge conversation:**

| Component | Tokens | Notes |
|-----------|--------|-------|
| Your question | 50 | "How should I price my SaaS at $99 or $149?" |
| Your approach | 200 | Your detailed reasoning |
| Merge instruction | 150 | System prompt with context |
| Past patterns (3) | 300 | Previous decisions |
| LLM research | 1000 | Web search results, calculations |
| LLM response | 800 | Merged analysis |
| **Total per merge** | **~2,500** | |

**Capacity:**
- GPT-4o: 128k tokens = ~50 merges before warning
- Claude Sonnet: 200k tokens = ~80 merges before warning

**v2 warns you at 100k tokens** (40 merges) to stay safe

---

## Recommendations

### Use v1 if:
- You want simple, working merge thinking NOW
- You don't need pattern learning
- Your conversations are short (<30 messages)

### Use v2 if:
- You make lots of decisions and want pattern learning
- You iterate on decisions ("what if I changed X?")
- You want token management and warnings
- You want merge history for future reference

### Future v3 (Phase 2):
- **Semantic search** on past merges (embeddings)
- **Open WebUI memory integration** (API calls)
- **RAG document retrieval** (query uploaded PDFs during merge)
- **Multi-model ensemble** (merge GPT + Claude perspectives)
- **Cost tracking** per merge session

---

## Which Should You Deploy?

**For Railway deployment NOW:** Use **v1**
- Battle-tested, simple, works
- You can upgrade to v2 later by just uploading new pipeline

**For local testing:** Try **v2**
- Test pattern learning
- See if multi-turn merge helps your workflow
- Validate token management

**Migration:** Zero downtime - just upload v2 pipeline, disable v1
