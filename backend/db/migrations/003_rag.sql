-- RAG documents
create table if not exists public.rag_documents (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.users(id) on delete cascade,
  source text not null,
  chunk_index int not null default 0,
  content text not null,
  content_hash text,
  embedding vector(1536),
  created_at timestamptz not null default now(),
  unique (user_id, source, chunk_index)
);

create index if not exists idx_rag_docs_user on public.rag_documents(user_id);
create index if not exists idx_rag_docs_embedding on public.rag_documents using hnsw (embedding vector_cosine_ops);

-- Semantic search over RAG documents
create or replace function public.match_rag_documents(
  query_embedding vector(1536),
  match_user_id uuid,
  match_threshold float default 0.7,
  match_count int default 5
) returns table (
  id uuid,
  content text,
  source text,
  similarity float
) as $$
  select id, content, source,
    1 - (embedding <=> query_embedding) as similarity
  from public.rag_documents
  where user_id = match_user_id
    and embedding is not null
    and 1 - (embedding <=> query_embedding) > match_threshold
  order by embedding <=> query_embedding
  limit match_count;
$$ language sql stable;

-- Hybrid search over relationship notes (semantic + keyword)
create or replace function public.hybrid_search_notes(
  query_text text,
  query_embedding vector(1536),
  match_user_id uuid,
  match_person_id uuid default null,
  semantic_weight float default 0.7,
  keyword_weight float default 0.3,
  match_count int default 8
) returns table (
  id uuid,
  person_id uuid,
  content text,
  extracted_facts jsonb,
  score float,
  created_at timestamptz
) as $$
  select
    rn.id,
    rn.person_id,
    rn.content,
    rn.extracted_facts,
    (
      semantic_weight * (1 - (rn.embedding <=> query_embedding)) +
      keyword_weight * ts_rank(to_tsvector('english', rn.content), plainto_tsquery('english', query_text))
    ) as score,
    rn.created_at
  from public.relationship_notes rn
  where rn.user_id = match_user_id
    and (match_person_id is null or rn.person_id = match_person_id)
    and rn.embedding is not null
  order by score desc
  limit match_count;
$$ language sql stable;

-- GIN index for full-text keyword search
create index if not exists idx_rel_notes_fts
  on public.relationship_notes
  using gin(to_tsvector('english', content));

-- Semantic search over relationship notes
create or replace function public.match_relationship_notes(
  query_embedding vector(1536),
  match_user_id uuid,
  match_person_id uuid default null,
  match_threshold float default 0.65,
  match_count int default 8
) returns table (
  id uuid,
  person_id uuid,
  content text,
  extracted_facts jsonb,
  similarity float,
  created_at timestamptz
) as $$
  select rn.id, rn.person_id, rn.content, rn.extracted_facts,
    1 - (rn.embedding <=> query_embedding) as similarity,
    rn.created_at
  from public.relationship_notes rn
  where rn.user_id = match_user_id
    and (match_person_id is null or rn.person_id = match_person_id)
    and rn.embedding is not null
    and 1 - (rn.embedding <=> query_embedding) > match_threshold
  order by rn.embedding <=> query_embedding
  limit match_count;
$$ language sql stable;
