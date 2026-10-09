"""
Seed initial structured memory files for Clifford.
Run once: python -m backend.scripts.seed_memory_files
Safe to re-run -- skips files that already exist.
"""
from dotenv import load_dotenv
load_dotenv()

from backend.memory.memory_files import create_memory_file

FILES = [
    {
        "category": "identity",
        "slug": "profile",
        "title": "Clifford's Profile",
        "summary": "Full name, background, education, Wema Bank role",
        "content": """# Clifford's Profile

- [stated] Full name: Chukwuma Clifford Nwanna, goes by Clifford
- [stated] Based in Lagos, Nigeria
- [stated] Degree in Electronics and Computer Engineering, Nnamdi Azikiwe University
- [stated] Completed 6-month GoMyCode data science bootcamp
- [stated] Prior role: Service Engineer at Coscharis Medical (2022 - Feb 2025)
- [stated] Chairs the CBN Data Localisation Committee internally at Wema Bank
- [stated] Runs Ecotronics Enterprise (entrepreneurial portfolio company)
- [stated] Prefers open-source and self-hosted solutions to minimise recurring costs
- [stated] Technical stack: Python, FastAPI, LangGraph, LangChain, Supabase, Azure,
  Microsoft Fabric, SQL Server, LLMs, RAG, embedded systems (ESP32, RFID)
""",
    },
    {
        "category": "employment",
        "slug": "employment",
        "title": "Employment",
        "summary": "Current and previous employers and roles",
        "content": """# Employment

- [stated, Mar 2025] Joined Wema Bank Plc as Data Scientist / AI Engineer
  (Executive Trainee), Data Analytics & AI team
- [stated] Prior: Service Engineer at Coscharis Medical (2022 - Feb 2025)
""",
    },
    {
        "category": "location",
        "slug": "location",
        "title": "Location",
        "summary": "Where Clifford is currently based",
        "content": """# Location

- [stated] Currently based in Lagos, Nigeria
""",
    },
    {
        "category": "goals",
        "slug": "migration",
        "title": "Australia Migration",
        "summary": "Engineers Australia pathway, CDR status, Cairns target",
        "content": """# Australia Migration

- [stated] Migrating to Australia via Engineers Australia (EA) skills assessment
- [stated] Target occupation: Electronics Engineer (ANZSCO 233411)
- [stated] CDR (Competency Demonstration Report): COMPLETE
- [stated] IELTS General Training target: Band 8
- [stated] Landing base: Cairns QLD - friend Charles has house and car
- [stated] Spouse relocating together
""",
    },
    {
        "category": "goals",
        "slug": "career",
        "title": "Career Goals",
        "summary": "Remote AI roles, income target, opportunity priorities",
        "content": """# Career Goals

- [stated] Target: remote AI/data science roles
- [stated] Income target: $10,000/month
""",
    },
    {
        "category": "projects",
        "slug": "upjobs",
        "title": "UpJobs.co",
        "summary": "AI job matching platform - needs users and revenue",
        "content": """# UpJobs.co

- [stated] AI job matching platform
- [stated] Currently live
- [stated] Needs users and revenue
""",
    },
    {
        "category": "projects",
        "slug": "jarvis",
        "title": "JARVIS",
        "summary": "Proactive personal AI assistant - this system",
        "content": """# JARVIS

- [stated] Proactive personal AI assistant
- [stated] This system - being built as a product
- [stated] Stack: FastAPI, LangGraph, Supabase, Mem0
""",
    },
    {
        "category": "projects",
        "slug": "gateman-v2",
        "title": "Gateman V2",
        "summary": "IoT attendance product under Ecotronics Enterprise",
        "content": """# Gateman V2

- [stated] IoT attendance product
- [stated] Under Ecotronics Enterprise
""",
    },
    {
        "category": "projects",
        "slug": "bodybalance",
        "title": "BodyBalance",
        "summary": "Multi-tenant AI clinic OS - Cherry's physio clinic is first tenant",
        "content": """# BodyBalance

- [stated] Multi-tenant AI clinic operating system
- [stated] Cherry's physiotherapy clinic is the first tenant
""",
    },
    {
        "category": "projects",
        "slug": "liveportfolio",
        "title": "LivePortfolio",
        "summary": "Portfolio builder platform",
        "content": """# LivePortfolio

- [stated] Portfolio builder platform
""",
    },
]


def seed():
    print(f"Seeding {len(FILES)} memory files...")
    created = 0
    skipped = 0
    for f in FILES:
        result = create_memory_file(
            slug=f["slug"],
            category=f["category"],
            title=f["title"],
            summary=f["summary"],
            initial_content=f["content"],
        )
        if "Created" in result:
            print(f"  [ok] {f['category']}/{f['slug']}")
            created += 1
        else:
            print(f"  [skip] {f['category']}/{f['slug']}: {result}")
            skipped += 1
    print(f"\nDone: {created} created, {skipped} skipped.")


if __name__ == "__main__":
    seed()
