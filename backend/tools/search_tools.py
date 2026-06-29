import os
import httpx
from langchain_core.tools import tool


@tool
async def web_search(query: str) -> str:
    """
    Search the web for current, real-time information.

    ALWAYS use this tool when the user asks about:
    - Current news, events, or recent developments
    - Exchange rates, stock prices, crypto prices
    - Weather in other cities (not current location)
    - Sports scores, match results
    - Any factual question that may have changed recently
    - Information about companies, people, or products
    - Anything you are not 100% certain about

    Args:
        query: A clear, specific search query in plain English.
               Examples: "Nigerian Naira to USD exchange rate today"
                         "latest news about OpenAI June 2026"
                         "Wema Bank Nigeria latest news"

    Returns:
        Search results as text with sources.
    """
    api_key = os.getenv("TAVILY_API_KEY")

    if api_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=5,
                include_answer=True,
            )
            parts = []
            if response.get("answer"):
                parts.append(f"Summary: {response['answer']}")
            for result in response.get("results", [])[:3]:
                parts.append(f"\n• {result.get('title', '')}: {result.get('content', '')[:200]}")
                if result.get("url"):
                    parts.append(f"  Source: {result['url']}")
            return "\n".join(parts) if parts else "No results found."
        except Exception as e:
            print(f"[web_search] Tavily error: {e}")

    # Fallback: DuckDuckGo Instant Answers
    return await _duckduckgo_search(query)


async def _duckduckgo_search(query: str) -> str:
    """Fallback DuckDuckGo search."""
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
        return f"Search unavailable: {e}"


@tool
async def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """
    Get the current exchange rate between two currencies.

    CALL THIS when user asks about:
    - "What is dollar to naira today?"
    - "NGN to USD rate"
    - "How much is X in Y currency?"
    - Any currency conversion question

    Uses open.er-api.com (free, no key required).
    from_currency: 3-letter code e.g. "NGN", "USD", "GBP"
    to_currency: 3-letter code e.g. "USD", "NGN", "EUR"
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"https://open.er-api.com/v6/latest/{from_currency.upper()}",
            )
            data = r.json()
            rate = data.get("rates", {}).get(to_currency.upper())
            if rate:
                return (
                    f"1 {from_currency.upper()} = {rate:.4f} {to_currency.upper()} "
                    f"(as of {data.get('time_last_update_utc', 'today')})"
                )
            return f"Could not find rate for {from_currency} to {to_currency}."
    except Exception as e:
        return f"Exchange rate unavailable: {e}"


@tool
async def calculate(expression: str) -> str:
    """
    Perform mathematical calculations safely.

    CALL THIS when user asks to:
    - Calculate, compute, or work out a number
    - "What is X + Y?"
    - "How much is X% of Y?"
    - Any arithmetic or percentage expression

    expression: a mathematical expression as a string
    Examples: "2500 * 1650", "15% of 50000", "sqrt(144)"
    """
    import ast
    import math

    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        allowed_names.update({"abs": abs, "round": round})

        expr = expression.replace("%", "/100").replace(" of ", "*")
        result = eval(
            compile(ast.parse(expr, mode="eval"), "<string>", "eval"),
            {"__builtins__": {}},
            allowed_names,
        )
        return f"{expression} = {result}"
    except Exception as e:
        return f"Could not calculate '{expression}': {e}"
