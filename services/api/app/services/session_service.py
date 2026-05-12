"""Per-session message history persistence (pydantic-ai ModelMessage serialization)."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Sequence

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

from app.database import get_db


async def load_history(session_id: str) -> list[ModelMessage]:
    """Return stored ModelMessage list for this session, or [] for a new session."""
    db = await get_db()
    try:
        async with db.execute(
            "SELECT messages_json FROM session_messages WHERE session_id = ?",
            (session_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return []
        return ModelMessagesTypeAdapter.validate_json(row["messages_json"])
    except Exception:
        return []
    finally:
        await db.close()


async def save_history(session_id: str, messages_json: bytes) -> None:
    """Upsert the full serialised message list for this session."""
    now = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO session_messages (session_id, messages_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                messages_json = excluded.messages_json,
                updated_at = excluded.updated_at
            """,
            (session_id, messages_json, now),
        )
        await db.execute(
            """
            INSERT INTO chat_sessions (session_id, created_at, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (session_id, now, now),
        )
        await db.commit()
    finally:
        await db.close()


async def clear_session(session_id: str) -> None:
    db = await get_db()
    try:
        await db.execute("DELETE FROM session_messages WHERE session_id = ?", (session_id,))
        await db.commit()
    finally:
        await db.close()
