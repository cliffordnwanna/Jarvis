"""
JARVIS Memory Discovery -- READ ONLY.

This module discovers relevant memory for a user query.
It NEVER creates, updates, appends, or deletes memory files.
All write operations go through file_tools.py, initiated by the agent.

Discovery strategy:
  1. Structured index pre-filter (cheap word overlap, fast path only)
  2. Mem0 semantic search (the real semantic engine)
  3. Formatted context with authority labels

The agent reasons over the combined context to determine relevance.
No keyword lists. No intent classifiers. No hardcoded routing.
"""
from __future__ import annotations


# Token budgets
STRUCTURED_MEMORY_BUDGET = 800
MEM0_MEMORY_BUDGET = 600
TOTAL_MEMORY_BUDGET = 1500


def _word_overlap_score(query: str, text: str) -> float:
    """
    Fast, cheap word overlap -- used as index pre-filter ONLY.
    Not semantic. Not for discovery of semantically similar content.
    Falls through to Mem0 when this returns low score.
    """
    query_words = set(w for w in query.lower().split() if len(w) > 3)
    text_words = set(w for w in text.lower().split() if len(w) > 3)
    if not query_words:
        return 0.0
    overlap = query_words & text_words
    return len(overlap) / len(query_words)


def find_structured_candidates(
    query: str,
    user_id: str,
    supabase,
    top_n: int = 2,
    threshold: float = 0.15,
) -> list[dict]:
    """
    Fast pre-filter: find memory files with word overlap against the query.
    Returns metadata only (no content). Content loaded separately if needed.

    LOW threshold (0.15) because this is an inclusion filter, not ranking.
    Semantic relevance comes from Mem0 -- this just surfaces obvious matches.
    When in doubt, include the candidate and let the agent decide.
    """
    try:
        result = (
            supabase
            .table("memory_files")
            .select("category, slug, title, summary, aliases, updated_at")
            .eq("user_id", user_id)
            .execute()
        )
        files = result.data or []
    except Exception as e:
        print(f"[discovery] index query error: {e}")
        return []

    scored = []
    for f in files:
        combined = f"{f.get('title', '')} {f.get('summary', '')}"
        aliases = f.get("aliases") or []
        alias_score = (
            max((1.0 if alias.lower() in query.lower() else 0.0) for alias in aliases)
            if aliases else 0.0
        )

        word_score = _word_overlap_score(query, combined)
        score = max(word_score, alias_score)

        if score >= threshold:
            scored.append({**f, "_score": score})

    scored.sort(key=lambda x: x["_score"], reverse=True)
    result_files = scored[:top_n]

    if result_files:
        print(
            f"[discovery] structured pre-filter: "
            f"matched={[f['slug'] for f in result_files]} "
            f"scores={[round(f['_score'], 2) for f in result_files]}"
        )
    else:
        print("[discovery] structured pre-filter: no matches — Mem0 is primary")

    return result_files


def format_memory_context(
    structured_files: list[dict],
    mem0_memories: str,
) -> str:
    """
    Format retrieved memory into a clearly-labelled context block.

    Structured memory: AUTHORITATIVE for current state.
    Mem0: SUPPORTING -- may contain older information.
    The agent uses authority labels to resolve conflicts.
    """
    sections = []

    if structured_files:
        sections.append(
            "## AUTHORITATIVE PERSONAL STATE\n"
            "[Structured memory — use this for current state. "
            "More recent than Mem0 for tracked categories.]\n"
        )
        for f in structured_files:
            updated = str(f.get("updated_at", ""))[:10]
            content = f.get("_content", f.get("summary", "[content not loaded]"))
            sections.append(f"**{f.get('title', f['slug'])}** [updated {updated}]:\n{content}\n")

    if mem0_memories:
        sections.append(
            "## SUPPORTING SEMANTIC MEMORY\n"
            "[Mem0 — may contain older information. "
            "Do not use to override AUTHORITATIVE STATE above.]\n"
            f"{mem0_memories}\n"
        )

    return "\n".join(sections) if sections else ""
