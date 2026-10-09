"""
Generate a short conversation title from the first user message.
Uses gpt-4o-mini — cheap, fast, non-blocking.
"""
from __future__ import annotations
import os
from openai import AsyncOpenAI

_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def generate_title(first_user_message: str) -> str:
    """Return a 2-6 word title. Never fails — returns fallback on any error."""
    try:
        resp = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a short conversation title (2-6 words, no punctuation, "
                        "no quotes) that captures the topic of the user's first message. "
                        "Reply with ONLY the title, nothing else."
                    ),
                },
                {"role": "user", "content": first_user_message[:500]},
            ],
            max_tokens=20,
            temperature=0.3,
        )
        title = resp.choices[0].message.content.strip().strip('"\'')
        return title if title else "New conversation"
    except Exception:
        return "New conversation"
