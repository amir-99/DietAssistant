from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import asyncio
import logging

from app.config import get_settings, Settings
from app.models.tracking import AssistantRequest, AssistantResponse
from app.agent.agent import get_agent
from app.agent.tools import AgentDeps
from app.services import session_service, memory_service, plan_meta_service, tracking_service

router = APIRouter(prefix="/assistant", tags=["assistant"])
logger = logging.getLogger(__name__)


def _require_workbook(settings: Settings = Depends(get_settings)):
    if not settings.workbook_path.exists():
        raise HTTPException(status_code=404, detail="No active diet plan. Upload a workbook first.")
    return settings


@router.post("/message", response_model=AssistantResponse)
async def chat(
    request: AssistantRequest,
    settings: Settings = Depends(_require_workbook),
):
    agent = get_agent()

    # ── 1. Load session history, memories, and calorie goal in parallel ───────
    history, memories, calorie_goal_val = await asyncio.gather(
        session_service.load_history(request.session_id),
        memory_service.get_all_memories(),
        plan_meta_service.get_plan_meta("daily_calorie_goal"),
    )
    memory_context = await memory_service.format_memory_context(memories)

    # Today's calorie total (synchronous — reads from Excel)
    import pytz
    from datetime import datetime
    tz_obj = pytz.timezone(settings.tz)
    today = request.date_override or datetime.now(tz_obj).strftime("%Y-%m-%d")
    try:
        events_today = tracking_service.get_events(str(settings.workbook_path), date_filter=today)
        total_calories_today = tracking_service.get_total_calories_today(events_today)
    except Exception:
        total_calories_today = 0.0

    deps = AgentDeps(
        workbook_path=str(settings.workbook_path),
        tz=settings.tz,
        confidence_auto=settings.match_confidence_auto,
        confidence_confirm=settings.match_confidence_confirm,
        date_override=request.date_override,
        memory_context=memory_context,
        calorie_goal=int(calorie_goal_val) if calorie_goal_val else 0,
        total_calories_today=total_calories_today,
    )

    # ── 2. Run agent with full conversation history ───────────────────────────
    try:
        result = await agent.run(
            request.message,
            message_history=history,
            deps=deps,
        )
        assistant_text = getattr(result, "output", None) or getattr(result, "data", "") or ""
        messages_json: bytes = result.all_messages_json()
    except Exception as exc:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=500, detail=f"Assistant error: {exc}")

    # ── 3. Persist session history and fire-and-forget memory extraction ──────
    await session_service.save_history(request.session_id, messages_json)
    asyncio.create_task(memory_service.extract_and_save(messages_json))

    return AssistantResponse(
        assistant_text=assistant_text,
        session_id=request.session_id,
    )


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear the conversation history for a session (start fresh)."""
    await session_service.clear_session(session_id)
    return {"cleared": True, "session_id": session_id}


@router.get("/memory")
async def get_memory():
    """Read all stored long-term memory facts."""
    return {"memories": await memory_service.get_all_memories()}


@router.delete("/memory/{key}")
async def forget_memory(key: str):
    """Delete a specific memory fact by key."""
    await memory_service.forget_memory(key)
    return {"forgotten": key}


@router.delete("/memory")
async def clear_all_memory():
    """Delete all long-term memory facts."""
    memories = await memory_service.get_all_memories()
    for key in memories:
        await memory_service.forget_memory(key)
    return {"cleared": len(memories)}
