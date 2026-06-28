# JARVIS v3 — Supabase Migration Checklist

Run each file in the Supabase SQL Editor in this exact order.
Dashboard → SQL Editor → New query → paste → Run.

## Step 1
File: backend/db/migrations/001_core.sql
Creates: users, goals, nudge_history, conversations, messages, world_state

## Step 2
File: backend/db/migrations/002_relationships.sql
Creates: people, relationship_notes, relationship_events, interaction_log
Also creates: contact frequency trigger, strength signal function

## Step 3
File: backend/db/migrations/003_rag.sql
Creates: rag_documents table, match_rag_documents RPC, match_relationship_notes RPC
Also adds: hybrid_search_notes function + GIN index

## Step 4
File: backend/db/migrations/004_rls.sql
Enables: Row Level Security on ALL tables
Creates: policies so users only see their own data
Creates: handle_new_user trigger (auto-creates profile on signup)

## Verify after running all 4:
Go to Supabase → Table Editor
You should see these tables:
- users
- goals
- nudge_history
- conversations
- messages
- world_state
- people
- relationship_notes
- relationship_events
- interaction_log
- rag_documents

If any table is missing, re-run that migration file.
