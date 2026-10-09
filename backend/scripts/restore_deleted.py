"""
One-time recovery script: restores the 10 memories wrongly deleted by the
lifecycle layer's over-eager _llm_supersedes() judgment during Phase 2
testing on 2026-10-08. Not part of the normal seed/startup path -- run
once, then delete this file.
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from backend.memory.mem0_client import get_memory, USER_ID

RESTORE = [
    "Clifford's prior role was Service Engineer at Coscharis Medical from 2022 to February 2025",
    "Clifford's career goal is to secure remote AI and data science roles with a target of $10,000 per month income",
    "Clifford is building UpJobs.co, an AI job matching platform",
    "Clifford is building JARVIS, a proactive personal AI assistant",
    "Clifford is building Gateman V2, an IoT attendance product under Ecotronics Enterprise",
    "Clifford runs Ecotronics Enterprise, his entrepreneurial portfolio company",
    "Clifford is based in Lagos, Nigeria",
    "Clifford is building BodyBalance, a multi-tenant AI clinic operating system, with Cherry's physio clinic as the first tenant",
    "Clifford is migrating to Australia via Engineers Australia EA skills assessment targeting Electronics Engineer ANZSCO 233411",
    "Clifford is building LivePortfolio, a portfolio builder platform",
]


def restore():
    m = get_memory()
    for fact in RESTORE:
        m.add([{"role": "user", "content": fact}], user_id=USER_ID)
        print(f"restored: {fact[:60]}...")


if __name__ == "__main__":
    restore()
