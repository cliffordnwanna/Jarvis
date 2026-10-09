"""
Structured memory files -- Claude-inspired approach.

One file per subject (employment, a project, a person, etc.)
Facts updated in place. Nothing deleted. History preserved in text.
Versioned to prevent concurrent write conflicts.

user_id is a real Supabase auth UUID (matching every other table in the
schema). Every function here REQUIRES it explicitly -- there is no
hardcoded default and no fallback user. Previously this module had a
module-level USER_ID constant that every function defaulted to, and the
LangChain @tool wrappers in file_tools.py never passed user_id at all --
meaning every memory-file operation for every user silently operated on
one hardcoded account (confirmed during the UUID/isolation audit; this
was the most severe finding, worse than the already-known "LLM-supplied
user_id is trusted" gap elsewhere, because here there was no user_id
plumbing of any kind, not even an untrusted one).
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from backend.db.postgres import get_supabase

# Valid categories. Expand only when needed.
CATEGORIES = {
    "identity":    "Stable personal facts (name, degree, background)",
    "employment":  "Current and historical employers and roles",
    "location":    "Current and previous locations",
    "projects":    "Active and completed projects",
    "goals":       "Current goals and aspirations",
    "preferences": "Stated preferences and working styles",
    "people":      "Important people in Clifford's life",
    "facts":       "Miscellaneous durable facts",
}


def get_memory_index(user_id: str) -> str:
    """
    Return a compact index of all memory files for this user.
    Injected into Layer 5 of the context builder at every turn.
    Token cost: ~5-10 tokens per file, negligible.
    """
    try:
        client = get_supabase()
        result = (
            client
            .table("memory_files")
            .select("category, slug, title, summary, updated_at")
            .eq("user_id", user_id)
            .order("category")
            .execute()
        )
        files = result.data or []
        if not files:
            return ""

        lines = ["## Memory Index (use read_memory_file_tool to see full content)"]
        current_cat = None
        for f in files:
            if f["category"] != current_cat:
                current_cat = f["category"]
                lines.append(f"\n### {current_cat.title()}")
            updated = f["updated_at"][:10] if f.get("updated_at") else ""
            lines.append(f"- **{f['title']}** [{updated}]: {f['summary']}")

        return "\n".join(lines)
    except Exception as e:
        print(f"[memory_files] index error (non-fatal): {e}")
        return ""


def read_memory_file(
    user_id: str,
    slug: str,
    category: str,
) -> str:
    """Read the full content of a memory file by slug and category."""
    try:
        client = get_supabase()
        result = (
            client
            .table("memory_files")
            .select("title, content, updated_at")
            .eq("user_id", user_id)
            .eq("category", category)
            .eq("slug", slug)
            .maybe_single()
            .execute()
        )
        if not result or not result.data:
            return f"No memory file found for {category}/{slug}"
        data = result.data
        updated = data.get("updated_at", "")[:10]
        return f"# {data['title']} [updated {updated}]\n\n{data['content']}"
    except Exception as e:
        return f"[memory_files] read error: {e}"


def update_memory_file(
    user_id: str,
    slug: str,
    category: str,
    old_line: str,
    new_line: str,
) -> str:
    """
    Update a specific line in a memory file.
    Replaces old_line with new_line. Old content preserved in new_line text.
    Returns success message or error.

    Versioned with an optimistic-lock guard: the write is conditioned on
    version still matching what was just read (.eq("version", version)),
    so a concurrent update (e.g. text and voice both editing the same file
    in the same window) can't silently overwrite the other's change --
    the second writer's conditioned update affects 0 rows instead, which
    is detected and reported as a conflict rather than silently "succeeding"
    while actually discarding the first writer's edit.

    If old_line is not found in the file: this is now a hard error, not a
    silent fallback to appending new_line. A near-miss (whitespace/
    punctuation difference from what's actually stored) used to produce a
    duplicate appended line while still reporting success -- the caller
    had no way to tell a real update from a silent fallback. Now it fails
    explicitly so the agent can re-read the file and retry with the exact
    text.
    """
    try:
        client = get_supabase()

        result = (
            client
            .table("memory_files")
            .select("content, version")
            .eq("user_id", user_id)
            .eq("category", category)
            .eq("slug", slug)
            .maybe_single()
            .execute()
        )
        if not result or not result.data:
            return f"Memory file {category}/{slug} not found. Use create_memory_file first."

        content = result.data["content"]
        version = result.data["version"]

        if old_line not in content:
            return (
                f"Update failed: old_line not found in {category}/{slug}. "
                f"No change was made. Re-read the file with read_memory_file_tool "
                f"and copy the exact line text before retrying."
            )

        new_content = content.replace(old_line, new_line, 1)

        update_result = (
            client
            .table("memory_files")
            .update({
                "content": new_content,
                "version": version + 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("user_id", user_id)
            .eq("category", category)
            .eq("slug", slug)
            .eq("version", version)
            .execute()
        )
        if not update_result.data:
            return (
                f"Update failed: {category}/{slug} was modified by another "
                f"request at the same time (version conflict). Re-read the "
                f"file and retry."
            )
        return f"Updated memory file {category}/{slug}"
    except Exception as e:
        return f"[memory_files] update error: {e}"


def append_to_memory_file(
    user_id: str,
    slug: str,
    category: str,
    new_line: str,
) -> str:
    """
    Append a new fact line to an existing memory file.
    Use when adding genuinely new information (not updating existing).

    Same optimistic-lock guard as update_memory_file -- the write is
    conditioned on version still matching the just-read value.
    """
    today = datetime.now(timezone.utc).strftime("%b %Y")
    tagged_line = f"- [stated, {today}] {new_line}"

    try:
        client = get_supabase()
        result = (
            client
            .table("memory_files")
            .select("content, version")
            .eq("user_id", user_id)
            .eq("category", category)
            .eq("slug", slug)
            .maybe_single()
            .execute()
        )
        if not result or not result.data:
            return f"Memory file {category}/{slug} not found."

        content = result.data["content"]
        version = result.data["version"]
        new_content = content.rstrip() + f"\n{tagged_line}"

        update_result = (
            client
            .table("memory_files")
            .update({
                "content": new_content,
                "version": version + 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("user_id", user_id)
            .eq("category", category)
            .eq("slug", slug)
            .eq("version", version)
            .execute()
        )
        if not update_result.data:
            return (
                f"Append failed: {category}/{slug} was modified by another "
                f"request at the same time (version conflict). Re-read the "
                f"file and retry."
            )
        return f"Appended to {category}/{slug}: {new_line}"
    except Exception as e:
        return f"[memory_files] append error: {e}"


def create_memory_file(
    user_id: str,
    slug: str,
    category: str,
    title: str,
    summary: str,
    initial_content: str,
) -> str:
    """
    Create a new memory file. Fails if slug+category already exists.
    Use update_memory_file for existing files.
    """
    if category not in CATEGORIES:
        return f"Unknown category '{category}'. Valid: {list(CATEGORIES.keys())}"

    try:
        client = get_supabase()
        client.table("memory_files").insert({
            "user_id": user_id,
            "category": category,
            "slug": slug,
            "title": title,
            "summary": summary,
            "content": initial_content,
        }).execute()
        return f"Created memory file {category}/{slug}"
    except Exception as e:
        return f"[memory_files] create error: {e}"
