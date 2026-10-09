"""
LangChain tools exposing memory files to the JARVIS agent.

The agent uses these to:
1. Read a specific memory file when answering a personal question
2. Update a file when the user states something new or corrected
3. Append new facts that don't conflict with existing ones
4. Create new files for new topics

Rules baked into docstrings (LLM reads these to decide when to call):
- Person questions -> also check hybrid_search_notes_tool
- Current state questions -> read the relevant memory file
- New fact from user -> append or update the relevant memory file
- Speculative statements ("I'm thinking of...") -> do NOT update files
- NEVER delete. Update in place, preserve history in the text.
"""
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from backend.memory.memory_files import (
    read_memory_file,
    update_memory_file,
    append_to_memory_file,
    create_memory_file,
    CATEGORIES,
)


@tool
def read_memory_file_tool(slug: str, category: str, user_id: Annotated[str, InjectedState("user_id")]) -> str:
    """
    Read a specific memory file to answer a personal question about Clifford.

    Use this when:
    - User asks about current employer, location, projects, goals, preferences
    - You see a relevant file in the memory index but need its full content
    - You need to check existing facts before deciding what to update

    Common slugs:
    - employment (category: employment) -- current and past employers
    - location (category: location) -- where Clifford lives
    - migration (category: goals) -- Australia migration plans
    - Any project name as slug (category: projects)
    - Any person's name as slug (category: people)

    Do NOT call this for every message -- only when a personal question
    is being asked that the memory index summary doesn't fully answer.

    Check the memory index in your context first. Only call this tool if a
    file is in the index but its content wasn't loaded into context.
    """
    return read_memory_file(user_id=user_id, slug=slug, category=category)


@tool
def update_memory_file_tool(
    user_id: Annotated[str, InjectedState("user_id")],
    slug: str,
    category: str,
    old_line: str,
    new_line: str,
) -> str:
    """
    Update a specific fact in a memory file when Clifford states a change.

    Use this ONLY when:
    - Clifford explicitly states a fact has changed ("I now work at...",
      "I've moved to...", "I left...", "I changed my mind about...")
    - You have read the file and identified the exact line to update
    - The new_line preserves history ("previously: X" or "[from: date]")

    Do NOT use this for:
    - Speculative statements ("I'm thinking of...", "I might...")
    - Adding new facts that don't conflict with existing ones (use append)
    - Anything you haven't first confirmed by reading the file

    old_line: exact text of the line being replaced (must match exactly)
    new_line: replacement text, preserving old value in brackets
              e.g. "- [stated, Oct 2026] Now works at Google as AI Engineer
                    [previously: Wema Bank, Mar 2025]"
    """
    return update_memory_file(
        user_id=user_id, slug=slug, category=category,
        old_line=old_line, new_line=new_line,
    )


@tool
def append_to_memory_file_tool(
    slug: str,
    category: str,
    new_fact: str,
    user_id: Annotated[str, InjectedState("user_id")],
) -> str:
    """
    Append a new fact to a memory file when Clifford states something new.

    Use this when:
    - Clifford shares a new fact that doesn't conflict with existing ones
    - Adding a new project, goal, preference, or relationship detail
    - The fact is definitively stated (not speculative)

    Do NOT use for updates to existing facts -- use update_memory_file_tool.
    Do NOT use for speculative statements.

    new_fact: the fact to record (do not include the bullet or date tag --
              those are added automatically)
    """
    return append_to_memory_file(user_id=user_id, slug=slug, category=category, new_line=new_fact)


@tool
def create_memory_file_tool(
    slug: str,
    category: str,
    title: str,
    summary: str,
    initial_content: str,
    user_id: Annotated[str, InjectedState("user_id")],
) -> str:
    """
    Create a new memory file for a topic not yet tracked.

    Valid categories: employment, location, projects, goals, preferences,
                      people, identity, facts

    Use this when:
    - Clifford mentions a new project not yet in the memory index
    - A new person is introduced who will be relevant across sessions
    - A new goal or major life area emerges

    initial_content: first facts in the file, formatted as:
    # Title
    - [stated, Month Year] fact here
    """
    return create_memory_file(
        user_id=user_id, slug=slug, category=category, title=title,
        summary=summary, initial_content=initial_content,
    )
