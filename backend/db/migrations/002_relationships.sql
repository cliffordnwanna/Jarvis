-- People
create table if not exists public.people (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.users(id) on delete cascade,
  name text not null,
  relationship_type text not null default 'friend'
    check (relationship_type in ('friend','family','colleague','mentor','acquaintance')),
  circle text not null default 'community'
    check (circle in ('inner','family','work','community')),
  birthday date,
  contact_frequency_days int,
  last_contacted_at timestamptz,
  strength_signal text not null default 'warm'
    check (strength_signal in ('warm','cooling','cold')),
  notes_summary text,
  phone text,
  email text,
  tags text[] default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Relationship notes
create table if not exists public.relationship_notes (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.users(id) on delete cascade,
  person_id uuid not null references public.people(id) on delete cascade,
  content text not null,
  extracted_facts jsonb default '[]',
  embedding vector(1536),
  source text not null default 'text'
    check (source in ('voice','text','chat_extraction','import')),
  created_at timestamptz not null default now()
);

-- Relationship events
create table if not exists public.relationship_events (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.users(id) on delete cascade,
  person_id uuid not null references public.people(id) on delete cascade,
  event_type text not null
    check (event_type in ('birthday','follow_up','call','meeting','occasion','check_in')),
  title text not null,
  scheduled_at timestamptz not null,
  completed_at timestamptz,
  nudge_sent boolean not null default false,
  context jsonb default '{}',
  created_at timestamptz not null default now()
);

-- Interaction log
create table if not exists public.interaction_log (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.users(id) on delete cascade,
  person_id uuid not null references public.people(id) on delete cascade,
  interaction_type text not null
    check (interaction_type in ('call','message','in_person','note')),
  notes text,
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

-- Now that people table exists, add FK from nudge_history.person_id
alter table public.nudge_history
  add constraint fk_nudge_person
  foreign key (person_id) references public.people(id) on delete set null;

-- Auto-set contact_frequency_days from circle when not provided
create or replace function public.default_contact_frequency(circle text) returns int as $$
  select case circle
    when 'inner'     then 7
    when 'family'    then 14
    when 'work'      then 30
    when 'community' then 60
    else 30
  end;
$$ language sql immutable;

create or replace function public.set_contact_frequency() returns trigger as $$
begin
  if new.contact_frequency_days is null then
    new.contact_frequency_days := public.default_contact_frequency(new.circle);
  end if;
  return new;
end;
$$ language plpgsql;

create trigger trg_set_contact_frequency
  before insert or update on public.people
  for each row execute function public.set_contact_frequency();

-- Nightly function to recompute strength signals (called by cron or admin script)
create or replace function public.recompute_strength_signals() returns void as $$
  update public.people
  set strength_signal = case
    when last_contacted_at is null then 'cold'
    when extract(epoch from (now() - last_contacted_at))/86400 <= contact_frequency_days then 'warm'
    when extract(epoch from (now() - last_contacted_at))/86400 <= contact_frequency_days * 2 then 'cooling'
    else 'cold'
  end,
  updated_at = now();
$$ language sql;

-- Indexes
create index if not exists idx_people_user on public.people(user_id);
create index if not exists idx_people_user_circle on public.people(user_id, circle);
create index if not exists idx_people_strength on public.people(user_id, strength_signal);
create index if not exists idx_rel_notes_person on public.relationship_notes(person_id);
create index if not exists idx_rel_notes_embedding on public.relationship_notes using hnsw (embedding vector_cosine_ops);
create index if not exists idx_rel_events_user_scheduled on public.relationship_events(user_id, scheduled_at);
create index if not exists idx_interaction_log_person on public.interaction_log(person_id);
