from langchain_core.tools import tool
import httpx


@tool
async def web_search(query: str) -> str:
    """Search the web for current information. Free, no API key needed."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1},
            headers={"User-Agent": "JARVIS/2.0"},
            timeout=5.0,
        )
        data = resp.json()
        results = data.get("RelatedTopics", [])[:3]
        snippets = [r.get("Text", "") for r in results if isinstance(r, dict)]
        return "\n".join(snippets) or "No results found."
