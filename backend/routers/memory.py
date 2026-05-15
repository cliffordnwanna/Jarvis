from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import os
import asyncpg

router = APIRouter(prefix="/memory", tags=["memory"])


class GoalIn(BaseModel):
    user_id: str
    name: str
    urgency: Optional[str] = "medium"


async def _get_conn():
    return await asyncpg.connect(os.getenv("DATABASE_URL", "postgresql://jarvis:jarvis@localhost:5432/jarvis").replace("+asyncpg", ""))


@router.get("/goals/{user_id}")
async def get_goals(user_id: str):
    conn = await _get_conn()
    rows = await conn.fetch(
        "SELECT id, name, status, urgency, last_touched_at FROM goals WHERE user_id=$1 AND status='active'",
        user_id,
    )
    await conn.close()
    return [dict(r) for r in rows]


@router.post("/goals")
async def create_goal(goal: GoalIn):
    conn = await _get_conn()
    row = await conn.fetchrow(
        "INSERT INTO goals (user_id, name, urgency) VALUES ($1, $2, $3) RETURNING id",
        goal.user_id, goal.name, goal.urgency,
    )
    await conn.close()
    return {"id": str(row["id"]), "name": goal.name}


@router.get("/patterns/{user_id}")
async def get_patterns(user_id: str):
    conn = await _get_conn()
    rows = await conn.fetch(
        "SELECT pattern_key, pattern_value, confidence FROM behavioral_patterns WHERE user_id=$1",
        user_id,
    )
    await conn.close()
    return [dict(r) for r in rows]
