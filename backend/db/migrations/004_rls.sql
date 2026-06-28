-- Enable RLS on all user tables
alter table public.users enable row level security;
alter table public.goals enable row level security;
alter table public.nudge_history enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.people enable row level security;
alter table public.relationship_notes enable row level security;
alter table public.relationship_events enable row level security;
alter table public.interaction_log enable row level security;
alter table public.rag_documents enable row level security;

-- Users: only see your own profile
create policy "users_own" on public.users
  for all using (auth.uid() = id);

-- Goals
create policy "goals_own" on public.goals
  for all using (auth.uid() = user_id);

-- Nudges
create policy "nudges_own" on public.nudge_history
  for all using (auth.uid() = user_id);

-- Conversations
create policy "conversations_own" on public.conversations
  for all using (auth.uid() = user_id);

-- Messages
create policy "messages_own" on public.messages
  for all using (auth.uid() = user_id);

-- People
create policy "people_own" on public.people
  for all using (auth.uid() = user_id);

-- Relationship notes
create policy "rel_notes_own" on public.relationship_notes
  for all using (auth.uid() = user_id);

-- Relationship events
create policy "rel_events_own" on public.relationship_events
  for all using (auth.uid() = user_id);

-- Interaction log
create policy "interaction_log_own" on public.interaction_log
  for all using (auth.uid() = user_id);

-- RAG documents
create policy "rag_docs_own" on public.rag_documents
  for all using (auth.uid() = user_id);

-- Auto-create user profile on Supabase Auth signup
create or replace function public.handle_new_user() returns trigger as $$
begin
  insert into public.users (id, display_name, timezone)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
    coalesce(new.raw_user_meta_data->>'timezone', 'Africa/Lagos')
  )
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer;

create or replace trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
