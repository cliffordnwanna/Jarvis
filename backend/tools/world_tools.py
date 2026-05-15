import uuid
from langchain_core.tools import tool


@tool
def update_world_state(world_state: dict) -> str:
    """Update the shared world state from incoming sensor data."""
    return f"World state updated with {len(world_state)} fields"


@tool
def send_nudge(
    nudge_type: str,
    message: str,
    card_data: dict,
    priority: str,
) -> str:
    """
    Send a proactive nudge card to the frontend UI.
    nudge_type: weather | food | traffic | goal | calendar
    priority: low | medium | high
    card_data: structured data the React card component will render
    """
    nudge_id = str(uuid.uuid4())
    return f"Nudge queued: {message} (id={nudge_id}, priority={priority})"
