import os
from supabase import create_client, Client

_client: Client | None = None


def get_supabase() -> Client:
    """
    Returns Supabase client using SERVICE_ROLE_KEY to bypass RLS.
    Auth is enforced at the FastAPI layer via JWT in auth.py — RLS is redundant here.
    """
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _client = create_client(url, key)
    return _client


def get_supabase_admin() -> Client:
    """
    Returns Supabase client using the SERVICE ROLE key, which bypasses RLS.
    Use only for admin operations (RAG embedding, migrations). Never in request handlers.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)
