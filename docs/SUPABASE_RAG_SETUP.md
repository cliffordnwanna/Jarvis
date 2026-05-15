# Supabase + RAG setup (Jarvis v2)

This guide sets up a **single, simple, robust** RAG architecture:

- Supabase Postgres stores your documents + embeddings (pgvector).
- Backend (`/llm/chat/completions`) injects:
  1) the canonical short prompt (`rag/system_short.md`)
  2) retrieved profile snippets (RAG) from Supabase

No separate vector DB. No complicated pipelines.

## 0) Prereqs

- A Supabase project
- An OpenAI API key (for embeddings)
- Your backend can reach Supabase Postgres over the network

## 1) Create Supabase project

1. Create a new project in Supabase.
2. Click **Connect** in the Supabase dashboard and copy a Postgres connection string (direct or pooler).

### Connection string choice (important)

Supabase offers **direct** and **pooler** URLs/modes.

- For a VPS / long-running backend: use **Direct** (if your network supports IPv6) or **Pooler session mode (port 5432)**.
- For serverless/edge style deployments: use **Pooler transaction mode (port 6543)**.
- Transaction mode does **not** support prepared statements; you must disable them.

If you use the pooler URL in transaction mode, add `?pgbouncer=true` to the connection string **or** set `DATABASE_PGBOUNCER=true` in this repo (it disables prepared statement caching in `asyncpg`).

Important: use the exact connection string Supabase shows in **Connect**.
- For poolers, the username is typically like `postgres.<project-ref>` (not plain `postgres`).
- Don’t mix a pooler host with a direct-connection username (or vice-versa), or DNS/auth will fail.

References:
- Supabase troubleshooting: “Disabling prepared statements” (search in Supabase docs)
- Supabase “Connection strings” docs

## 2) Enable required Postgres extensions

You need two extensions:

- `pgcrypto` (for `gen_random_uuid()`)
- `vector` (pgvector)

You can enable extensions in either of these ways:

### Option A: Supabase UI (recommended)

Go to **Database → Extensions**, search and enable:
- `pgcrypto`
- `vector`

### Option B: SQL editor

In Supabase **SQL editor**, run:

```sql
create extension if not exists pgcrypto;
create extension if not exists vector;
```

If you enabled them in the UI already, the SQL above is harmless.

## 3) Create the RAG table + index

In Supabase **SQL editor**, run the SQL from:

- `backend/db/migrations/002_rag.sql`

Notes:
- The table uses `vector(1536)` by default because `text-embedding-3-small` embeddings are 1536-dimensional by default.
- The HNSW index uses cosine distance operator `<=>` / `vector_cosine_ops` (pgvector).

References:
- OpenAI docs: Embeddings guide (default dimensions)
- Supabase docs: HNSW indexes (pgvector operators)

## 4) Configure backend environment variables

Set these in your backend environment (`.env` or your host’s env config):

```bash
# Required
DATABASE_URL="postgresql://...your supabase connection string..."
OPENAI_API_KEY="sk-..."

# Embeddings
OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
OPENAI_EMBEDDING_DIMENSIONS="1536"

# If using Supabase transaction pooler (6543)
DATABASE_PGBOUNCER="true"

# RAG behavior
RAG_ENABLED="true"
RAG_USER_ID="default"
RAG_TOP_K="5"
RAG_MIN_SIMILARITY="0.78"
RAG_MAX_CONTEXT_CHARS="2400"
RAG_CHUNK_TARGET_CHARS="2400"
```

## 5) Ingest your seed truth (documents → embeddings → Supabase)

This repo already contains the seed truth files:

- `rag/system_short.md`
- `rag/clifford_profile.md`
- `rag/migration_plan.md`

The ingester also automatically extracts and ingests your long prompt from:

- `backend/agent.py#SYSTEM_PROMPT`

Run ingestion from the repo root:

```bash
python -m backend.scripts.rag_ingest
```

Expected output includes per-source chunk counts and upserts.

## 6) Verify retrieval is working (fast sanity checks)

Once the backend is running, ask in the UI:

- “Where do I want to relocate to?”
- “What’s my target ANZSCO?”
- “What’s my IELTS target?”

If RAG is working, these answers come back even when they’re not in the short prompt, because the backend injects retrieved context per question.

## 7) Keeping it efficient (don’t bloat tokens)

This architecture is designed to keep token usage low:

- The short prompt is always injected.
- RAG injects **only top‑K** chunks, capped by `RAG_MAX_CONTEXT_CHARS`.
- Retrieval is based on cosine similarity using `<=>`.

If retrieval is too “chatty”:
- reduce `RAG_TOP_K` (e.g., 3)
- increase `RAG_MIN_SIMILARITY` (e.g., 0.82)
- reduce `RAG_MAX_CONTEXT_CHARS` (e.g., 1600)
