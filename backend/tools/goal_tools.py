import uuid
from langchain_core.tools import tool


@tool
def manage_goals(goals: list[dict]) -> str:
    """Replace entire goals list. Use to add, update or remove goals."""
    for g in goals:
        if not g.get("id"):
            g["id"] = str(uuid.uuid4())
    return f"Goals updated: {len(goals)} total"


@tool
def get_goals() -> list[dict]:
    """Read the current goals list before making changes."""
    return []
