# JARVIS — Local Development & Operations Reference

All commands are run from **`C:\Ecotronics Enterprise\Jarvis`** (repo root) unless stated otherwise.

---

## 1. Start Backend (FastAPI)

```powershell
# From repo root
uvicorn backend.main:app --reload --port 8000
```

Backend runs at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

---

## 2. Start Frontend (Next.js)

```powershell
# From the frontend folder
cd frontend
npm run dev
```

Frontend runs at: `http://localhost:3000`

To return to repo root after:
```powershell
cd ..
```

---

## 3. Start Redis

Redis is required for nudges and session memory. Start it via Docker before the backend.

```powershell
# From repo root — starts only the Redis container
docker compose up redis -d
```

Verify it's running:
```powershell
docker compose ps
```

Stop Redis:
```powershell
docker compose stop redis
```

> If you don't have Docker, install [Docker Desktop](https://www.docker.com/products/docker-desktop/) — it's the easiest option on Windows.

---

## 4. Run Everything Together (three terminals)

**Terminal 1 — Redis (start first, from repo root):**
```powershell
docker compose up redis -d
```

**Terminal 2 — Backend (repo root):**
```powershell
uvicorn backend.main:app --reload --port 8000
```

**Terminal 3 — Frontend:**
```powershell
cd frontend
npm run dev
```

---

## 5. RAG — Ingest Knowledge Files

Run this every time you update any file in `rag/` or `backend/agent.py`.

```powershell
# From repo root
$env:RAG_CHUNK_TARGET_CHARS="600"
python -m backend.scripts.rag_ingest
```

Expected output:
```
RAG ingest: user_id=default
Sources=5 target_chars=600
- rag/clifford_profile.md: chunks=N upserted=N
- rag/migration_plan.md:   chunks=N upserted=N
- rag/products.md:         chunks=N upserted=N
- rag/income_strategy.md:  chunks=N upserted=N
- rag/system_short.md:     chunks=N upserted=N
- backend/agent.py#SYSTEM_PROMPT: chunks=N upserted=N
Done.
```

---

## 5. RAG — Validate Retrieval (Eval)

Run this after every ingest to confirm retrieval accuracy.

```powershell
# From repo root
python -m backend.scripts.rag_eval
```

Target: **32/34 or better**. Any FAIL shows which keywords are missing from retrieval.

---

## 6. RAG — Enable / Disable

In `.env` (repo root):

```env
RAG_ENABLED=true    # JARVIS pulls profile context on every request
RAG_ENABLED=false   # Disabled (use during debugging)
```

Restart backend after changing.

---

## 7. Knowledge Files — What to Update and When

These live in `rag/`. Edit them in any text editor, then re-ingest.

| File | What it contains | Update when |
|------|-----------------|-------------|
| `rag/clifford_profile.md` | Skills, identity, tools, hardware stack | You learn a new skill or tool |
| `rag/migration_plan.md` | EA/ACS status, visa, IELTS, milestones | EA submitted / IELTS booked / status changes |
| `rag/products.md` | UpJobs, Ecotronics SAS, Gateman, JARVIS | Product stage changes, revenue, new features |
| `rag/income_strategy.md` | Salary, savings, income targets, freelance positioning | First client landed / SaaS revenue / salary change |
| `rag/system_short.md` | Short always-injected JARVIS identity + key facts | Major life/profile changes |
| `backend/agent.py` | Full JARVIS system prompt with all rules | Communication rules, priorities change |

**Workflow:**
```
1. Edit the relevant rag/*.md file
2. python -m backend.scripts.rag_ingest   (from repo root)
3. python -m backend.scripts.rag_eval     (verify)
4. Restart backend
```

---

## 8. Supabase — Check RAG Table

Run in **Supabase SQL Editor** (`supabase.com → your project → SQL Editor`):

```sql
-- See all stored chunks
SELECT source, chunk_index, length(content) AS chars, left(content, 80) AS preview
FROM rag_documents
WHERE user_id = 'default'
ORDER BY source, chunk_index;

-- Count chunks per source
SELECT source, count(*) AS chunks
FROM rag_documents
WHERE user_id = 'default'
GROUP BY source ORDER BY source;
```

**To wipe and re-ingest from scratch** (always do this before a full re-ingest):
```sql
DELETE FROM rag_documents WHERE user_id = 'default';
```
Then re-run `rag_ingest`.

---

## 9. Install Dependencies (first time or after pull)

**Backend:**
```powershell
# From repo root
pip install -r backend/requirements.txt
```

**Frontend:**
```powershell
cd frontend
npm install
cd ..
```

---

## 10. Environment Variables (`.env` in repo root)

Key variables — all required for full functionality:

```env
# OpenAI — LLM completions (gpt-4o-mini) + RAG embeddings (text-embedding-3-small)
OPENAI_API_KEY=...

# Supabase (RAG storage)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...

# RAG
RAG_ENABLED=true
RAG_SIMILARITY_THRESHOLD=0.2
RAG_CHUNK_TARGET_CHARS=600

# CopilotKit
COPILOTKIT_API_KEY=...

# Redis (nudges / memory)
REDIS_URL=redis://localhost:6379
```

---

## 11. Git — Save Your Work

```powershell
git add backend/agent.py rag/ backend/rag.py backend/scripts/ backend/routers/
git commit -m "describe what changed"
```

---

## Quick Reference Card

| Task | Command | Folder |
|------|---------|--------|
| Start Redis | `docker compose up redis -d` | repo root |
| Start backend | `uvicorn backend.main:app --reload --port 8000` | repo root |
| Start frontend | `npm run dev` | `frontend/` |
| Re-ingest RAG | `$env:RAG_CHUNK_TARGET_CHARS="600"; python -m backend.scripts.rag_ingest` | repo root |
| Validate RAG | `python -m backend.scripts.rag_eval` | repo root |
| Wipe RAG data | SQL: `DELETE FROM rag_documents WHERE user_id = 'default'` | Supabase SQL Editor |
| Install backend deps | `pip install -r backend/requirements.txt` | repo root |
| Install frontend deps | `npm install` | `frontend/` |
