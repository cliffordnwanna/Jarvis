-- Supabase PostgREST RPC for vector similarity search
-- Used by backend/rag.py via /rest/v1/rpc/match_rag_documents

CREATE OR REPLACE FUNCTION match_rag_documents(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    p_user_id text
)
RETURNS TABLE (
    source text,
    chunk_index int,
    content text,
    similarity float
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    d.source,
    d.chunk_index,
    d.content,
    (1 - (d.embedding <=> query_embedding)) AS similarity
  FROM rag_documents d
  WHERE d.user_id = p_user_id
    AND (1 - (d.embedding <=> query_embedding)) >= match_threshold
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
$$;

