-- Structured memory files: canonical facts organized by category.
-- Each file = one subject (employment, projects, goals, etc.)
-- Facts updated in place -- nothing deleted, history preserved in text.
--
-- user_id is uuid with a real FK to public.users(id), matching every other
-- table in this schema (001_core.sql, 002_relationships.sql, 003_rag.sql all
-- use `user_id uuid not null references public.users(id)`). The Mem0 system
-- in backend/memory/mem0_client.py currently hardcodes USER_ID="clifford" as
-- a plain string, a pre-existing simplification from earlier work -- this
-- table deliberately does not follow that convention, by explicit decision,
-- since schema-level FK integrity matters more here than matching Mem0's
-- current (non-ideal) scoping.

CREATE TABLE IF NOT EXISTS public.memory_files (
    id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    category    text NOT NULL,
    slug        text NOT NULL,        -- e.g. "employment", "cherry", "upjobs"
    title       text NOT NULL,        -- e.g. "Employment", "Cherry (Sister)"
    summary     text NOT NULL,        -- one-line description for the index
    content     text NOT NULL,        -- structured facts (see format below)
    aliases     text[] DEFAULT '{}',  -- other names this file responds to
    updated_at  timestamptz DEFAULT now(),
    version     integer DEFAULT 1,

    UNIQUE(user_id, category, slug)
);

CREATE INDEX IF NOT EXISTS idx_memory_files_user ON public.memory_files(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_files_user_category ON public.memory_files(user_id, category);

-- RLS included for defense-in-depth, matching every other table in this
-- schema -- but functionally inert here the same way it is everywhere else:
-- backend/db/postgres.py's get_supabase() always uses the service-role key,
-- which bypasses RLS. Real authorization happens at the FastAPI layer via
-- get_current_user() (backend/auth.py), not via these policies.
ALTER TABLE public.memory_files ENABLE ROW LEVEL SECURITY;
CREATE POLICY memory_files_own ON public.memory_files
    FOR ALL USING (auth.uid() = user_id);
