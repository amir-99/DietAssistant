"""Persist and retrieve plan-level metadata (calorie goal, etc.) in plan_meta SQLite table."""
from __future__ import annotations
from app.database import get_db


async def get_plan_meta(key: str) -> str | None:
    db = await get_db()
    try:
        async with db.execute("SELECT value FROM plan_meta WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
        return row["value"] if row else None
    finally:
        await db.close()


async def set_plan_meta(key: str, value: str) -> None:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO plan_meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()
    finally:
        await db.close()
