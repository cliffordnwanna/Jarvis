from langchain_core.tools import tool
import httpx


@tool
async def web_search(query: str) -> str:
    """Search the web for current information using DuckDuckGo Instant Answers."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            data = r.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                return abstract
            results = data.get("RelatedTopics", [])[:3]
            texts = [t.get("Text", "") for t in results if isinstance(t, dict) and t.get("Text")]
            return " | ".join(texts) if texts else "No results found."
    except Exception as e:
        return f"Search error: {e}"
