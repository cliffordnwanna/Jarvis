-- RAG / Vector search tables (Supabase Postgres + pgvector)
-- Assumes OpenAI `text-embedding-3-small` default dimensionality (1536).

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL DEFAULT 'default',
    source TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, source, chunk_index)
);

-- Fast cosine similarity search (optional for small corpora)
-- Requires pgvector >= 0.5.0 (available on Supabase).
CREATE INDEX IF NOT EXISTS rag_documents_embedding_hnsw
  ON rag_documents USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS rag_documents_user_source_idx
  ON rag_documents (user_id, source);
