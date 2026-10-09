"""
One-time seed: load Clifford's core facts into Mem0.

This seeds initial data. JARVIS will update these facts automatically as
you tell it new information -- the data lives in Supabase, not in this
script; skipping it entirely and letting JARVIS learn from conversation
is a valid choice too.

Run:
    python -m backend.scripts.seed_mem0            # skip facts that already exist
    python -m backend.scripts.seed_mem0 --clear     # wipe all memories first, then seed
"""
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from backend.memory.mem0_client import get_memory, USER_ID, delete_all

FACTS = [
    "Clifford's full name is Chukwuma Clifford Nwanna, goes by Clifford",
    "Clifford works at Wema Bank Plc as a Data Scientist / AI Engineer (Executive Trainee), started March 2025",
    "Clifford is migrating to Australia via Engineers Australia (EA) skills assessment, targeting Electronics Engineer ANZSCO 233411",
    "Clifford's CDR (Competency Demonstration Report) for Engineers Australia is complete",
    "Clifford's IELTS target is Band 8 General Training",
    "Clifford's planned landing base in Australia is Cairns QLD, where his friend Charles lives and has a house and car",
    "Clifford's spouse is relocating to Australia with him",
    "Clifford's degree is in Electronics and Computer Engineering from Nnamdi Azikiwe University",
    "Clifford completed a 6-month GoMyCode data science bootcamp",
    "Clifford's prior role was Service Engineer at Coscharis Medical (2022 to February 2025)",
    "Clifford is building UpJobs.co — an AI job matching platform",
    "Clifford is building JARVIS — a proactive personal AI assistant (this system)",
    "Clifford is building Gateman V2 — an IoT attendance product under Ecotronics Enterprise",
    "Clifford is building BodyBalance — a multi-tenant AI clinic operating system, with Cherry's physio clinic as the first tenant",
    "Clifford is building LivePortfolio — a portfolio builder platform",
    "Clifford runs Ecotronics Enterprise, his entrepreneurial portfolio company",
    "Clifford's career goal is remote AI/data science roles with a target of $10,000 per month income",
    "Clifford prefers open-source and self-hosted solutions to minimise recurring costs",
    "Clifford is based in Lagos, Nigeria",
    "Clifford chairs the CBN Data Localisation Committee internally at Wema Bank",
    "Clifford's technical stack includes Python, FastAPI, LangGraph, LangChain, Supabase, Azure, Microsoft Fabric, SQL Server, LLMs, RAG, and embedded systems including ESP32 and RFID",
]


def _already_exists(m, fact: str) -> bool:
    """Check via search whether a near-identical memory already exists."""
    try:
        results = m.search(fact, filters={"user_id": USER_ID}, limit=1)
        matches = results.get("results", [])
        if not matches:
            return False
        # mem0's search returns a similarity score; treat a close match as
        # "already seeded" rather than inserting a near-duplicate.
        return matches[0].get("score", 0) >= 0.85
    except Exception:
        return False


async def seed(clear: bool = False) -> None:
    print("This seeds initial data. JARVIS will update these facts automatically as you tell it new information.")

    if clear:
        print("--clear passed: wiping all existing memories first...")
        deleted = await delete_all()
        print(f"  Deleted {deleted} existing memories.")

    m = get_memory()
    print(f"Seeding {len(FACTS)} facts into Mem0 for user_id={USER_ID}...")
    added, skipped, failed = 0, 0, 0
    for i, fact in enumerate(FACTS, 1):
        try:
            if not clear and _already_exists(m, fact):
                print(f"  [{i}/{len(FACTS)}] - skipped (already exists): {fact[:60]}...")
                skipped += 1
                continue
            m.add([{"role": "user", "content": fact}], user_id=USER_ID)
            print(f"  [{i}/{len(FACTS)}] ✓ {fact[:70]}")
            added += 1
        except Exception as e:
            print(f"  [{i}/{len(FACTS)}] ✗ ERROR: {e}")
            failed += 1
    print(f"Seeding complete. added={added} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    clear_flag = "--clear" in sys.argv
    asyncio.run(seed(clear=clear_flag))
