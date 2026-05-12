"""Cross-session long-term memory: extract and persist user facts between conversations."""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.database import get_db
from app.config import get_settings

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = (
    "You are a memory extraction assistant. "
    "Given a diet-tracking conversation, extract key facts about the user "
    "that are worth remembering across future sessions. "
    "Focus on: dietary preferences, intolerances, favourite foods, meal timing habits, "
    "portion preferences, plan compliance patterns, personal goals, and any personal details shared. "
    "Return ONLY a flat JSON object whose keys are short snake_case fact names and values are "
    "concise strings. Example: {\"prefers_light_breakfast\": \"yes\", \"avoids\": \"dairy\"}. "
    "If nothing memorable was said, return {}."
)


async def get_all_memories() -> dict[str, str]:
    """Load all stored user memory facts from DB."""
    db = await get_db()
    try:
        async with db.execute("SELECT key, value FROM user_memory") as cur:
            rows = await cur.fetchall()
        return {row["key"]: row["value"] for row in rows}
    except Exception:
        return {}
    finally:
        await db.close()


async def format_memory_context(memories: dict[str, str]) -> str:
    """Format memories for injection into the system prompt."""
    if not memories:
        return ""
    lines = [f"- {k.replace('_', ' ')}: {v}" for k, v in memories.items()]
    return "\n".join(lines)


async def save_memories(facts: dict[str, str]) -> None:
    if not facts:
        return
    now = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    try:
        for key, value in facts.items():
            if not key or not value:
                continue
            await db.execute(
                """
                INSERT INTO user_memory (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (str(key)[:100], str(value)[:500], now),
            )
        await db.commit()
    finally:
        await db.close()


async def forget_memory(key: str) -> None:
    db = await get_db()
    try:
        await db.execute("DELETE FROM user_memory WHERE key = ?", (key,))
        await db.commit()
    finally:
        await db.close()


async def extract_and_save(messages_json: bytes) -> None:
    """
    Background task: call the LLM to extract memorable facts from the latest
    conversation turn and persist them to user_memory.
    """
    settings = get_settings()
    try:
        # Build a plain-text conversation snippet for the extraction prompt
        from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelRequest, ModelResponse
        messages = ModelMessagesTypeAdapter.validate_json(messages_json)

        lines: list[str] = []
        for msg in messages[-20:]:          # only last 20 to keep context small
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    text = getattr(part, "content", None)
                    if isinstance(text, str) and text.strip():
                        lines.append(f"User: {text.strip()}")
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    text = getattr(part, "content", None)
                    if isinstance(text, str) and text.strip():
                        lines.append(f"Assistant: {text.strip()}")

        if not lines:
            return

        conversation_text = "\n".join(lines)

        if settings.llm_provider == "openai":
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=settings.openai_api_key or None,
                base_url=settings.llm_base_url or None,
            )
            resp = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM},
                    {"role": "user", "content": conversation_text},
                ],
                max_tokens=400,
                temperature=0,
            )
            raw = resp.choices[0].message.content or "{}"
        else:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(
                api_key=settings.anthropic_api_key or None,
                base_url=settings.llm_base_url or None,
            )
            resp = await client.messages.create(
                model=settings.llm_model,
                system=EXTRACTION_SYSTEM,
                messages=[{"role": "user", "content": conversation_text}],
                max_tokens=400,
            )
            raw = resp.content[0].text if resp.content else "{}"

        # Parse JSON — be tolerant of markdown fences
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        facts = json.loads(raw)
        if isinstance(facts, dict):
            await save_memories(facts)
            logger.info("Memory extraction saved %d fact(s)", len(facts))

    except Exception as exc:
        logger.warning("Memory extraction failed (non-fatal): %s", exc)
