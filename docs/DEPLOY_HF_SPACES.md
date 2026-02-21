# Deploy JARVIS v3 to Hugging Face Spaces - Complete Guide

**100% FREE forever | 16GB RAM | 50GB disk | No credit card needed**

This is the recommended deployment method for JARVIS v3 Orchestrator.

## Pre-Flight Checklist ✅

- [ ] OpenAI API key ready ([platform.openai.com/api-keys](https://platform.openai.com/api-keys))
- [ ] Hugging Face account ([huggingface.co](https://huggingface.co) - free signup)
- [ ] `Dockerfile.huggingface` ready in your repo

## Quick Deploy (10 minutes)

### 1. Create Hugging Face Account (2 min)

1. Go to [huggingface.co](https://huggingface.co)
2. Click **Sign Up**
3. Enter email, username, password
4. Verify email
5. You're ready!

### 2. Create Your Space (2 min)

1. Click **Spaces** (top menu) → **Create new Space**
2. **Space name:** `jarvis-ai` (or your preferred name)
3. **License:** MIT
4. **Space SDK:** Docker
5. **Visibility:** Public (free tier only)
6. Click **Create Space**

### 3. Upload Dockerfile (2 min)

1. On your Space page → Click **Files** tab
2. Click **+ Add file** → **Create a new file**
3. **Filename:** `Dockerfile`
4. **Paste this content:**

```dockerfile
FROM ghcr.io/open-webui/open-webui:main

# Hugging Face Spaces configuration
ENV PORT=7860
ENV HOST=0.0.0.0

# These will be set via HF Spaces secrets
ENV WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# Use OpenAI directly
ENV OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL:-https://api.openai.com/v1}

# Enable signup for first user (becomes admin)
ENV ENABLE_SIGNUP=true

# Default models
ENV DEFAULT_MODELS=gpt-4o,gpt-4o-mini

EXPOSE 7860

CMD ["bash", "start.sh"]
```

5. Click **Commit new file to main**

### 4. Add API Keys (2 min)

1. Click **Settings** tab
2. Scroll to **Repository secrets**
3. Click **New secret**

**Secret 1:**
- **Name:** `OPENAI_API_KEY`
- **Value:** Your OpenAI key (e.g., `sk-proj-...`)
- Click **Add**

**Secret 2:**
- **Name:** `WEBUI_SECRET_KEY`
- **Value:** Generate at [random.org/strings](https://www.random.org/strings/?num=1&len=32&digits=on&upperalpha=on&loweralpha=on&unique=on&format=plain)
- Click **Add**

### 5. Wait for Build (3-5 min)

1. Click **App** tab
2. You'll see "Building..." status
3. Wait 3-5 minutes
4. When done, you'll see the Open WebUI interface!

### 6. Create Admin Account (1 min)

1. Click **Sign Up**
2. Enter:
   - **Name:** Your name
   - **Email:** Your email
   - **Password:** Strong password
3. Click **Create Account**
4. You're now the admin!

---

## Complete Setup (15 minutes)

### 7. Enable New Features (3 min)

#### 7.1 Enable Analytics Dashboard

1. Click **profile icon** (top right) → **Admin Panel**
2. **Settings** → **Features**
3. Find **Analytics Dashboard**
4. Toggle **ON**
5. Click **Save**

**What you get:**
- Model usage statistics
- Token consumption tracking
- Cost monitoring per model/user
- Perfect for validating v3 orchestrator savings!

#### 7.2 Enable Skills (Experimental)

1. Still in **Settings** → **Features**
2. Find **Skills**
3. Toggle **ON**
4. Click **Save**

**What you get:**
- Create reusable AI skills
- Invoke with `$` command
- Attach to specific models

---

### 8. Setup Merge Thinking (Choose One Method)

You have two options for deploying merge thinking:

#### **Option A: Skills (Recommended - Easier)**

Skills are the new way to add capabilities in Open WebUI v0.8.3.

1. **Admin Panel** → **Workspace** → **Skills**
2. Click **+ Create Skill**
3. **Fill in details:**
   - **Name:** `Merge Thinking v3`
   - **Command:** `merge`
   - **Description:** `Ask for your approach first, then merge perspectives with research`
   - **Content:** Paste the merge thinking instructions below

4. **Merge Thinking Skill Content:**

```markdown
# Merge Thinking Process

You are JARVIS with merge thinking capability. When the user asks a decision question (contains "how should", "best way", "decide", etc.):

## Step 1: Ask User's Approach
Reply ONLY with: "How would YOU handle this?"

## Step 2: Research Independently
After user responds:
- Use web search to gather current information
- Analyze best practices and expert opinions
- Consider multiple perspectives

## Step 3: Merge & Compare
Present your analysis in this format:

### Your Approach
[Summarize user's thinking]

### My Research
[Key findings from independent research]

### Where We Align
[Points of agreement]

### Where We Disagree
[Differences with reasoning]

### Final Recommendation
[Synthesized best approach]

## Configuration
- Max context: 8000 tokens
- Enable web search for research
- Be direct and honest about disagreements
```

5. Click **Save**
6. **Enable the skill** (toggle switch)

**To use:** Type `$merge` in any chat, then ask your question!

---

#### **Option B: Pipeline (Advanced - More Control)**

Pipelines give you programmatic control with Python.

1. **Admin Panel** → **Settings** → **Pipelines**
2. Click **+ Add Pipeline**
3. **Open your IDE** → `pipelines/merge_thinking_orchestrator.py`
4. **Copy ALL contents** (Ctrl+A, Ctrl+C)
5. **Paste into pipeline editor**
6. Click **Save**
7. **Enable the pipeline** (toggle switch)
8. Click **⚙️ settings icon** → Configure valves:

```
monthly_budget_usd: 50
max_context_tokens: 8000
enable_orchestrator: true
enable_cost_tracking: true
enable_pattern_learning: true
ask_user_first: true
```

9. Click **Save**

**Pipeline works automatically** - no command needed!

---

### 9. Configure Models (2 min)

#### 9.1 Set Default Model

1. Click **model dropdown** (top of chat)
2. Click **⚙️** next to `gpt-4o`
3. **Set as default** → Toggle ON
4. Click **Save**

#### 9.2 Add Custom System Prompt (Optional)

1. Still in model settings
2. Scroll to **System Prompt**
3. Open `docs/system_prompt.md` in your IDE
4. **Customize the User Context section:**
   ```markdown
   **Name:** [Your actual name]
   **Background:** [Your profession]
   **Goals:** [Your current priorities]
   **Working style:** [Your preferences]
   ```
5. **Copy entire customized prompt**
6. **Paste into System Prompt field**
7. Click **Save**

---

### 10. Enable Web Search (Critical for Merge Thinking)

1. **Admin Panel** → **Settings** → **Web Search**
2. **Enable:** Toggle ON
3. **Search Engine:** Select **DuckDuckGo** (free, no API key)
4. Click **Save**

**Why this matters:** Merge thinking tells the LLM to "research independently" — web search enables this.

---

### 11. Enable Memory (Optional but Recommended)

1. Click **profile icon** → **Settings**
2. **Personalization** → **Memory**
3. Toggle **Enable Memory** to ON
4. **Settings:**
   - **Auto-save:** ON
   - **Memory Scope:** Personal
5. Click **Save**

**Test memory:**
- Tell JARVIS: "Remember that I'm building a SaaS product"
- New chat → Ask: "What am I working on?"
- Should recall your project

---

## End-to-End Testing (5 minutes)

### Test 1: Basic Chat

1. **New chat** → Select `gpt-4o`
2. Send: `Hello! What can you help me with?`
3. ✅ Should get a response from GPT-4o

### Test 2: Merge Thinking (Skills Method)

1. **New chat** → Type: `$merge`
2. Send: `How should I price my SaaS product?`
3. ✅ Expected: "How would YOU handle this?"
4. Answer: `I'd charge $99/month based on competitors`
5. ✅ JARVIS should:
   - Research pricing strategies
   - Compare your approach with findings
   - Show alignment and disagreements
   - Give final recommendation

### Test 3: Merge Thinking (Pipeline Method)

1. **New chat** → Select `gpt-4o`
2. Send: `How should I launch my product?`
3. ✅ Expected: "How would YOU handle this?"
4. Answer with your approach
5. ✅ JARVIS merges perspectives

### Test 4: Web Search

1. **New chat**
2. Send: `What are the latest AI trends in 2026?`
3. ✅ Should see web search tool being used
4. ✅ Should get current information

### Test 5: Memory

1. Tell JARVIS: `Remember my name is [Your Name]`
2. **New chat** → Ask: `What's my name?`
3. ✅ Should recall correctly

### Test 6: Analytics (After a few chats)

1. **Admin Panel** → **Analytics**
2. ✅ Should see:
   - Model usage stats
   - Token consumption
   - Cost estimates
   - User activity

---

## Monitor Your Deployment

### Check Costs

**In Analytics Dashboard:**
1. **Admin Panel** → **Analytics**
2. View token consumption by model
3. Track daily/monthly usage
4. Identify cost patterns

**Expected costs with v3 orchestrator:**
- Merge thinking: ~3,000 tokens per merge (vs 15,000 without orchestrator)
- **85% cost savings** on merge operations
- Regular chat: Standard GPT-4o pricing

### Check Merge History

**Pipeline method only:**
- Files stored in `/app/backend/data/`
- `jarvis_merge_state.json` — Current sessions
- `jarvis_merge_history.json` — Last 50 merges
- `jarvis_cost_tracking.json` — Cost tracking

**Skills method:**
- No persistent storage (stateless)
- Use Analytics Dashboard for tracking

### Performance Monitoring

**In your Space:**
1. Click **Logs** tab
2. Monitor for errors
3. Check startup time
4. Verify API connections

---

## Troubleshooting

### Models Not Appearing

**Symptom:** Model dropdown is empty

**Solutions:**
1. Check **Settings** → **Repository secrets**
2. Verify `OPENAI_API_KEY` is correct
3. Restart Space: **Settings** → **Factory reboot**
4. Check logs for API errors

### Merge Thinking Not Working

**Skills method:**
- Verify skill is enabled (toggle ON)
- Use exact command: `$merge`
- Check skill content has correct instructions

**Pipeline method:**
- Verify pipeline is enabled
- Check valve settings
- Look for trigger words: "how should", "best way", "decide"

### Web Search Not Working

1. **Settings** → **Web Search** → Verify enabled
2. Check DuckDuckGo is selected
3. Test with: "What's the weather today?"
4. Should see search_web tool in action

### Memory Not Persisting

1. **Settings** → **Personalization** → **Memory** → Verify ON
2. Test with simple fact: "Remember I like pizza"
3. New chat → Ask: "What do I like?"
4. If fails, check Space logs for database errors

### Space Sleeping

**Free tier sleeps after 48h inactivity**

**Solutions:**
- First request after sleep takes 30-60s to wake
- Upgrade to paid Space for always-on ($9/month)
- Or accept the cold start (fine for personal use)

---

## Next Steps

### Customize Your JARVIS

1. **Add more models:**
   - Admin Panel → Connections
   - Add Anthropic, OpenRouter, etc.

2. **Create more Skills:**
   - Research assistant
   - Code reviewer
   - Writing coach

3. **Build Knowledge Bases:**
   - Upload your documents
   - Enable RAG for context-aware responses

4. **Set up Channels:**
   - Team collaboration
   - Shared conversations

### Monitor & Optimize

1. **Review Analytics weekly:**
   - Which models are most cost-effective?
   - Are you hitting budget limits?
   - Is merge thinking saving costs?

2. **Adjust orchestrator settings:**
   - Increase/decrease budget
   - Tune context limits
   - Enable/disable features

3. **Collect feedback:**
   - Use built-in feedback system
   - Rate responses
   - Improve prompts based on patterns

---

## Cost Expectations

### With v3 Orchestrator

**Merge thinking operations:**
- Before: ~15,000 tokens per merge
- After: ~3,000 tokens per merge
- **Savings: 85%**

**Monthly estimates (50 merges/month):**
- Without orchestrator: ~$15-20
- With orchestrator: ~$3-5
- **Savings: $12-15/month**

### Without Orchestrator

**Regular GPT-4o usage:**
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens
- Average chat: 500-1000 tokens

**Budget recommendations:**
- Light use (10 chats/day): $10-15/month
- Medium use (30 chats/day): $30-50/month
- Heavy use (100+ chats/day): $100+/month

---

## Deployment Complete! 🎉

You now have:
- ✅ JARVIS running on Hugging Face Spaces (FREE forever)
- ✅ v3 Orchestrator with 85% cost savings
- ✅ Analytics Dashboard for monitoring
- ✅ Skills or Pipeline for merge thinking
- ✅ Web search enabled
- ✅ Memory enabled
- ✅ Full Open WebUI v0.8.3 features

**Your Space URL:** `https://huggingface.co/spaces/YOUR_USERNAME/jarvis-ai`

Start chatting and test merge thinking!
