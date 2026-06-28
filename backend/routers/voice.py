from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
import httpx
import os

router = APIRouter()


@router.get("/token")
async def get_voice_token(user_id: str = Depends(get_current_user)):
    """
    Generate an ephemeral OpenAI Realtime API token.
    The frontend uses this to connect directly via WebRTC.
    The real API key never leaves the backend.
    """
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "voice": "alloy",
            },
            timeout=10.0,
        )
        if res.status_code != 200:
            raise HTTPException(502, f"OpenAI token error: {res.text}")
        return res.json()
