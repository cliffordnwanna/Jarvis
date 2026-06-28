-- Enable extensions
create extension if not exists vector;
create extension if not exists "uuid-ossp";

-- Users (mirrors Supabase auth.users)
create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  timezone text not null default 'Africa/Lagos',
  morning_nudge_time time not null default '08:00:00',
  home_lat float8,
  home_lng float8,
  work_lat float8,
  work_lng float8,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Goals
create table if not exists public.goals (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.users(id) on delete cascade,
  title text not null,
  status text not null default 'active' check (status in ('active','paused','completed')),
  urgency text not null default 'medium' check (urgency in ('low','medium','high')),
  last_touched_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

-- Nudge history
create table if not exists public.nudge_history (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.users(id) on delete cascade,
  nudge_type text not null,
  person_id uuid,  -- FK added in 002_relationships.sql after people table exists
  message text not null,
  priority text not null default 'medium' check (priority in ('low','medium','high')),
  delivered_at timestamptz not null default now(),
  dismissed_at timestamptz,
  actioned boolean not null default false
);

-- Conversations
create table if not exists public.conversations (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.users(id) on delete cascade,
  title text,
  created_at timestamptz not null default now(),
  last_message_at timestamptz not null default now()
);

-- Messages
create table if not exists public.messages (
  id uuid primary key default uuid_generate_v4(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  role text not null check (role in ('user','assistant','tool')),
  content text not null,
  meta jsonb default '{}',
  created_at timestamptz not null default now()
);

-- World state cache (replaces Redis)
create table if not exists public.world_state (
  user_id uuid primary key references public.users(id) on delete cascade,
  state jsonb not null default '{}',
  updated_at timestamptz not null default now()
);

alter table public.world_state enable row level security;
create policy "world_state_own" on public.world_state
  for all using (auth.uid() = user_id);

-- Indexes
create index if not exists idx_goals_user on public.goals(user_id);
create index if not exists idx_goals_user_status on public.goals(user_id, status);
create index if not exists idx_nudges_user on public.nudge_history(user_id);
create index if not exists idx_nudges_user_dismissed on public.nudge_history(user_id, dismissed_at);
create index if not exists idx_messages_conversation on public.messages(conversation_id, created_at);
create index if not exists idx_conversations_user on public.conversations(user_id, last_message_at desc);
