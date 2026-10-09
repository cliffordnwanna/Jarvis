"""
Local dev entrypoint for Windows. psycopg3's async mode requires a
selector-based event loop; Windows' default ProactorEventLoop is
incompatible. This must be set before uvicorn (or anything else) creates
an event loop — importing uvicorn lazily, after the policy is set, is
what guarantees that ordering. Not used in production (the VPS is Linux,
where this is a no-op) — deploy/start.sh keeps using the uvicorn CLI directly.
"""
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, loop="asyncio")
