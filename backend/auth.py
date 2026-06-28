import os
from fastapi import Header, HTTPException
from supabase import create_client

_auth_client = None


def _get_auth_client():
    global _auth_client
    if _auth_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        _auth_client = create_client(url, key)
    return _auth_client


async def get_current_user(authorization: str = Header(None)) -> str:
    """
    FastAPI dependency. Validates the Supabase JWT from the Authorization header
    and returns the authenticated user's UUID.

    Usage in routers:
        @router.get("/")
        async def handler(user_id: str = Depends(get_current_user)):
            ...
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    try:
        client = _get_auth_client()
        res = client.auth.get_user(token)
        if not res or not res.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return res.user.id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Token validation failed")
