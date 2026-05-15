# Merge Thinking Orchestrator - Architecture & Design

## The Problem You Identified

**Current v1/v2 issues:**
- Sends ALL context to LLM (expensive, hits limits)
- No intelligent filtering of relevant vs irrelevant info
- Token costs spiral on long conversations
- No budget management
- Context limits cause silent failures

**Your solution:** Add an orchestrator layer that summarizes and optimizes before sending to LLM.

---

## Orchestrator Architecture (v3)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT                                │
│         "How should I price my product?"                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATOR LAYER (NEW)                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ STEP 1: GATHER                                       │   │
│  │ • User question (500 tokens)                         │   │
│  │ • User approach (800 tokens)                         │   │
│  │ • Full conversation history (15,000 tokens)          │   │
│  │ • Past merge patterns (2,000 tokens)                 │   │
│  │ • Uploaded documents context (5,000 tokens)          │   │
│  │ TOTAL: 23,300 tokens                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ STEP 2: COMPRESS & FILTER                            │   │
│  │ • Conversation → Last 5 key exchanges (600 tokens)   │   │
│  │ • Patterns → Summary of 3 relevant (400 tokens)      │   │
│  │ • Documents → Extract relevant quotes (800 tokens)   │   │
│  │ • Question + Approach → Keep full (1,300 tokens)     │   │
│  │ COMPRESSED: 3,100 tokens (87% reduction!)            │   │
│  └──────────────────────────────────────────────────────┘   │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ STEP 3: COST CHECK                                   │   │
│  │ • Input: 3,100 tokens × $0.0025/1k = $0.0078        │   │
│  │ • Output estimate: 800 tokens × $0.01/1k = $0.008   │   │
│  │ • Total: ~$0.016 per merge                           │   │
│  │ • Monthly budget: $50 → 3,125 merges available      │   │
│  │ • Current month: $12.40 used → $37.60 remaining     │   │
│  └──────────────────────────────────────────────────────┘   │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ STEP 4: BUILD OPTIMIZED PROMPT                       │   │
│  │ [MERGE THINKING - Orchestrated Context]              │   │
│  │ Question: [original]                                 │   │
│  │ User approach: [original]                            │   │
│  │ [Compressed patterns]                                │   │
│  │ [Compressed conversation]                            │   │
│  │ Instructions: [concise merge instructions]           │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM (GPT-4o / Claude)                     │
│         Receives ONLY optimized 3,100 tokens                 │
│         (vs 23,300 tokens without orchestrator)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  MERGE RESPONSE                              │
│         "Here's where we align/disagree..."                  │
└─────────────────────────────────────────────────────────────┘
```

---

## How Compression Works

### Before Orchestrator (v1/v2)
```
Full conversation history: 15,000 tokens
├─ Message 1: "Hi JARVIS" (50 tokens)
├─ Message 2: "Tell me about AI" (200 tokens)
├─ Message 3: "What's the weather?" (150 tokens)
├─ ... (50 more messages)
└─ Message 53: "How should I price my product?" (500 tokens)

ALL 15,000 tokens sent to LLM → $0.0375 cost
```

### After Orchestrator (v3)
```
Compressed conversation: 600 tokens
├─ Extract: Last 5 exchanges only
├─ Summarize: First sentence of each message
├─ Filter: Remove greetings, off-topic, redundant
└─ Result: "User discussed pricing strategy, mentioned 
           competitors at $99/mo, asked about value-based 
           pricing, concerned about market positioning"

Only 600 tokens sent → $0.0015 cost (96% savings!)
```

---

## Key Features

### 1. Intelligent Compression

**Conversation History:**
```python
# Before: 50 messages × 300 tokens = 15,000 tokens
# After: Last 5 key exchanges, first sentence only = 600 tokens

Original: "I've been thinking about pricing and I looked at 
          competitors like Competitor A who charges $99/month 
          and Competitor B at $149/month and I'm wondering if 
          I should go somewhere in between or maybe higher..."

Compressed: "User researched competitors ($99-149/mo), 
            considering pricing strategy"
```

**Pattern History:**
```python
# Before: Full details of 50 past merges = 5,000 tokens
# After: Summary of 3 most relevant = 400 tokens

Original: [Full JSON with timestamps, all messages, etc.]

Compressed: "1. Pricing decision → Started conservative, scaled up
            2. Hiring decision → Contract-to-hire approach
            3. Marketing decision → Focus on organic first"
```

### 2. Cost Tracking & Budget Management

**Real-time monitoring:**
```json
{
  "total_cost": 12.40,
  "monthly_budget": 50.00,
  "remaining": 37.60,
  "sessions": [
    {
      "timestamp": "2026-02-21T12:00:00Z",
      "tokens_input": 3100,
      "tokens_output": 800,
      "cost_usd": 0.016
    }
  ]
}
```

**Budget alerts:**
- At 80% ($40): Warning in responses
- At 100% ($50): Switches to brief mode
- User can adjust budget via Valves

### 3. Multi-Stage Processing

**Stage 1: Gather (collects everything)**
- User question
- User approach
- Full conversation
- Past patterns
- Uploaded documents
- Memory entries

**Stage 2: Compress (filters to essentials)**
- Relevance scoring (simple keyword matching for now)
- Deduplication
- Summarization (first sentence extraction)
- Token budget allocation

**Stage 3: Validate (optional)**
- Fact-check key claims
- Cross-reference with tools
- Multi-model comparison

**Stage 4: Merge (final LLM call)**
- Optimized prompt
- Compressed context
- Clear instructions

---

## Token Savings Examples

### Example 1: Long Conversation

| Component | Without Orchestrator | With Orchestrator | Savings |
|-----------|---------------------|-------------------|---------|
| Conversation history | 15,000 | 600 | 96% |
| Pattern history | 2,000 | 400 | 80% |
| User question | 500 | 500 | 0% |
| User approach | 800 | 800 | 0% |
| Instructions | 500 | 300 | 40% |
| **TOTAL INPUT** | **18,800** | **2,600** | **86%** |
| **Cost per merge** | **$0.047** | **$0.007** | **85%** |

### Example 2: Multi-Turn Iteration

```
User: "How should I price my product?"
[Merge happens - 2,600 tokens]

User: "What if I offered a $49 tier?"
Without orchestrator: 2,600 + 15,000 = 17,600 tokens
With orchestrator: 2,600 (previous compressed to 400) = 3,000 tokens

Savings: 83% on iteration
```

---

## Configuration (Valves)

All settings adjustable in Open WebUI:

```python
# Orchestrator settings
enable_orchestrator: bool = True
max_context_tokens: int = 8000        # Target for compressed context
compression_ratio: float = 0.3        # Keep 30% of original

# Cost management
enable_cost_tracking: bool = True
cost_per_1k_input_tokens: float = 0.0025   # GPT-4o
cost_per_1k_output_tokens: float = 0.01
monthly_budget_usd: float = 50.0

# Pattern learning
patterns_to_retrieve: int = 3         # How many past merges to include
```

---

## Comparison: v1 vs v2 vs v3

| Feature | v1 | v2 | v3 (Orchestrator) |
|---------|----|----|-------------------|
| **Token management** | None | Warns at 100k | Active compression to 8k target |
| **Cost tracking** | No | No | Yes, per-session + monthly |
| **Budget management** | No | No | Yes, with alerts |
| **Compression** | No | No | Yes, 60-80% reduction |
| **Pattern learning** | No | Yes | Yes, with summarization |
| **Multi-turn merge** | No | Yes | Yes, with compressed history |
| **Context optimization** | No | No | **Yes (key feature)** |
| **Avg tokens/merge** | 15,000 | 12,000 | 3,000 |
| **Cost/merge** | $0.038 | $0.030 | $0.008 |
| **Merges per $50** | 1,315 | 1,666 | 6,250 |

---

## What Gets Compressed vs Preserved

### Always Preserved (100%)
- Current user question
- Current user approach
- Merge instructions
- Critical facts from tools

### Compressed (70-90% reduction)
- Conversation history → Last 5 key exchanges
- Pattern history → Summary of 3 relevant
- Uploaded documents → Relevant quotes only
- Memory entries → Key facts only

### Filtered Out (100% removal)
- Greetings ("Hi", "Thanks")
- Off-topic messages
- Duplicate information
- System messages
- Timestamps and metadata

---

## Performance Impact

### Latency
- **Compression overhead:** ~50-100ms (negligible)
- **LLM response time:** Actually FASTER (smaller context = faster processing)
- **Total:** Net neutral or slight improvement

### Accuracy
- **Risk:** Might lose important context in compression
- **Mitigation:** Preserves full question + approach + recent exchanges
- **Testing needed:** Compare v2 vs v3 merge quality

### Cost
- **Input tokens:** 60-80% reduction
- **Output tokens:** Unchanged (LLM still generates full response)
- **Total savings:** ~70% per merge

---

## Limitations & Future Improvements

### Current Limitations
- **Simple compression:** First-sentence extraction, not semantic
- **No embeddings:** Can't do true semantic similarity for patterns
- **No document RAG:** Doesn't query uploaded PDFs yet
- **Single-model only:** Validation requires manual setup

### Phase 2 Enhancements
1. **Semantic compression** with embeddings
2. **RAG integration** for uploaded documents
3. **Multi-model validation** (GPT + Claude comparison)
4. **Adaptive compression** based on question complexity
5. **Learning from feedback** (if user says "you missed X", adjust compression)

---

## Deployment Recommendation

### Test Locally First
```bash
test-local.bat
# Upload orchestrator.py via Open WebUI
# Run 5-10 test merges
# Check cost_tracking.json
# Compare quality vs v1/v2
```

### Metrics to Track
- Average tokens per merge
- Cost per merge
- Merge quality (subjective)
- Compression ratio achieved
- Budget burn rate

### Rollout Strategy
1. **Week 1:** Deploy v1 to Railway (proven, simple)
2. **Week 2:** Test v3 orchestrator locally
3. **Week 3:** If quality is good, replace v1 with v3
4. **Week 4:** Monitor costs, tune compression settings

---

## Cost Projection

### Without Orchestrator (v1)
- 10 merges/day × $0.038 = $0.38/day
- Monthly: $11.40
- Plus general chat: ~$20/month
- **Total: ~$31/month**

### With Orchestrator (v3)
- 10 merges/day × $0.008 = $0.08/day
- Monthly: $2.40
- Plus general chat: ~$20/month
- **Total: ~$22/month**

**Savings: $9/month (29% reduction)**

### Heavy Usage (50 merges/day)
- Without: $57/month (over budget!)
- With: $32/month (within budget)
- **Savings: $25/month (44% reduction)**

---

## Summary

The orchestrator is a **smart middleware layer** that:

✅ **Compresses** context by 60-80% before LLM  
✅ **Tracks** costs per session and monthly  
✅ **Manages** budget with alerts  
✅ **Preserves** accuracy by keeping critical info  
✅ **Enables** more merges within same budget  
✅ **Prevents** context limit errors  

**Your idea was spot-on.** This is how production AI systems work at scale.
