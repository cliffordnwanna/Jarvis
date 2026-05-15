-- Vector similarity search via RPC — called by the backend over HTTPS.
-- Required when using Supabase REST API instead of direct Postgres connection.

create or replace function match_rag_documents(
  query_embedding vector(1536),
  match_threshold float,
  match_count      int,
  p_user_id        text default 'default'
)
returns table (
  source      text,
  chunk_index integer,
  content     text,
  similarity  float
)
language sql stable
as $$
  select
    source,
    chunk_index,
    content,
    1 - (embedding <=> query_embedding) as similarity
  from rag_documents
  where
    user_id = p_user_id
    and 1 - (embedding <=> query_embedding) > match_threshold
  order by embedding <=> query_embedding
  limit match_count;
$$;
