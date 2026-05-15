"""
RAG retrieval validation — run after ingestion to confirm accuracy.

Usage:
    python -m backend.scripts.rag_eval

Prints PASS/FAIL per test case with similarity scores.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=REPO_ROOT / ".env", override=True)

from backend.rag import similarity_search

# Each tuple: (query, keywords that MUST appear in top results)
TEST_CASES: list[tuple[str, list[str]]] = [
    # --- Identity & background ---
    ("Who is Clifford?",                                    ["clifford", "engineer"]),
    ("Where is Clifford based?",                           ["lagos", "nigeria"]),
    ("What is Clifford's full name?",                      ["chukwuma", "nwanna"]),

    # --- Skills ---
    ("What programming languages does Clifford know?",     ["python", "sql"]),
    ("What AI frameworks does Clifford use?",              ["langchain", "openai"]),
    ("What hardware skills does Clifford have?",           ["esp32", "rfid"]),
    ("What embedded systems platforms does Clifford use?", ["esp32", "arduino"]),
    ("What data tools does Clifford use?",                 ["power bi", "sql server"]),
    ("What cloud platforms does Clifford work with?",      ["supabase", "docker"]),

    # --- Employment ---
    ("What is Clifford's current employer?",               ["wema", "bank"]),
    ("What does Clifford do at Wema Bank?",                ["ai", "analytics"]),

    # --- Products ---
    ("What products is Clifford building?",                ["upjobs", "ecotronics"]),
    ("What is UpJobs?",                                    ["job", "african"]),
    ("What problem does UpJobs solve?",                    ["ats", "remote"]),
    ("What is the Smart Attendance System?",               ["attendance", "biometric"]),
    ("What is Ecotronics Enterprise?",                     ["ecotronics", "iot"]),
    ("What is Gateman?",                                   ["access", "rfid"]),

    # --- Migration ---
    ("Where does Clifford want to relocate?",              ["australia", "cairns"]),
    ("What is Clifford's target ANZSCO occupation?",       ["233411", "electronics engineer"]),
    ("What is Clifford's IELTS band target?",              ["band 8", "ielts"]),
    ("What is CDR status for Engineers Australia?",        ["complete", "cdr"]),
    ("What backup migration pathway is there?",            ["acs"]),
    ("What visa subclasses is Clifford targeting?",        ["482", "190"]),
    ("What is the employer sponsored visa option?",        ["482", "employer"]),

    # --- Financials ---
    ("What is Clifford's current salary?",                 ["540", "naira"]),
    ("How much money does Clifford need for Australia?",   ["18,000", "aud"]),
    ("What is Clifford's monthly income target?",          ["3,000"]),
    ("What are Clifford's income phase targets?",          ["phase", "10,000"]),

    # --- Income strategy ---
    ("What freelance platforms should Clifford use?",      ["upwork", "toptal"]),
    ("What income channels is Clifford pursuing?",         ["freelance", "saas"]),
    ("What grants can Clifford apply for?",                ["grants", "startup"]),
    ("What is Clifford's freelance niche?",                ["ai automation", "intelligent"]),
    ("What are Clifford's top priorities?",                ["money", "australia"]),
    ("What makes Clifford's profile unique?",              ["hardware", "rare"]),
]


async def main() -> None:
    user_id = os.getenv("RAG_USER_ID", "default")
    min_sim = float(os.getenv("RAG_EVAL_MIN_SIM", "0.40"))
    top_k = int(os.getenv("RAG_EVAL_TOP_K", "5"))

    print(f"RAG eval  user_id={user_id}  top_k={top_k}  min_sim={min_sim}\n")

    passed = failed = 0

    for query, required_keywords in TEST_CASES:
        results = await similarity_search(user_id=user_id, query=query, top_k=top_k)
        above_threshold = [r for r in results if r.get("similarity", 0) >= min_sim]
        combined = " ".join(r["content"].lower() for r in above_threshold)

        hits = [kw for kw in required_keywords if kw.lower() in combined]
        ok = len(hits) == len(required_keywords)

        if ok:
            passed += 1
        else:
            failed += 1

        status = "PASS" if ok else "FAIL"
        sims = [f"{r['similarity']:.3f}" for r in results]
        missing = [kw for kw in required_keywords if kw.lower() not in combined]

        print(f"[{status}] {query}")
        print(f"       similarities : {sims}")
        if missing:
            print(f"       missing words: {missing}")
            if results:
                print(f"       top snippet  : {results[0]['content'][:150].strip()!r}")
        print()

    total = passed + failed
    print(f"{'='*50}")
    print(f"Result: {passed}/{total} passed")
    if failed:
        print()
        print("Troubleshooting tips:")
        print("  - Lower RAG_EVAL_MIN_SIM (currently {:.2f})".format(min_sim))
        print("  - Increase RAG_EVAL_TOP_K in your env")
        print("  - Re-run ingestion: python -m backend.scripts.rag_ingest")
    else:
        print("All tests passed. RAG is ready.")


if __name__ == "__main__":
    asyncio.run(main())
