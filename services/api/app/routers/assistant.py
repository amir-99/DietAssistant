from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
import asyncio
import json
import logging

from app.config import get_settings, Settings
from app.models.tracking import AssistantRequest, AssistantResponse, ReasoningStep
from app.agent.agent import get_agent
from app.agent.tools import AgentDeps
from app.services import session_service, memory_service, plan_meta_service, tracking_service

router = APIRouter(prefix="/assistant", tags=["assistant"])
logger = logging.getLogger(__name__)

_TOOL_META = {
    "match_consumption_to_plan": ("🔍", "Matching meals to your plan"),
    "log_consumption":           ("✅", "Logging meals"),
    "get_daily_status":          ("📊", "Checking daily progress"),
    "search_plan_options":       ("🔎", "Searching plan options"),
    "search_parsed_plan_items":  ("🔎", "Searching food items"),
    "get_plan_option":           ("📋", "Getting option details"),
    "get_plan_sections":         ("📋", "Getting plan sections"),
    "correct_consumption":       ("✏️", "Correcting an entry"),
    "delete_consumption":        ("🗑️", "Removing an entry"),
    "build_advice_context":      ("💡", "Analysing your day"),
}


def _args_summary(tool_name: str, args: dict) -> str:
    if tool_name == "match_consumption_to_plan":
        return f"\"{args.get('user_text', '')[:80]}\""
    if tool_name == "log_consumption":
        entries = args.get("entries", [])
        return f"{len(entries)} item(s) to log"
    if tool_name == "get_daily_status":
        return f"date: {args.get('date', 'today')}"
    if tool_name in ("search_plan_options", "search_parsed_plan_items"):
        return f"\"{args.get('query', '')[:60]}\""
    if tool_name == "get_plan_option":
        return f"{args.get('section', '')} #{args.get('option_no', '')}"
    if tool_name in ("correct_consumption", "delete_consumption"):
        return f"event {args.get('event_id', '')}"
    return str(args)[:100]


def _result_summary(tool_name: str, content) -> str:
    if not isinstance(content, dict):
        return str(content)[:150]

    if tool_name == "match_consumption_to_plan":
        opts = content.get("matched_options", [])
        items = content.get("matched_items", [])
        needs = content.get("needs_confirmation", False)
        parts = []
        if opts:
            best = opts[0].get("confidence", 0)
            parts.append(f"{len(opts)} option match(es) — best {best:.0f}%")
        if items:
            best = items[0].get("confidence", 0)
            parts.append(f"{len(items)} item match(es) — best {best:.0f}%")
        if not parts:
            parts.append("No matches found in plan")
        if needs:
            parts.append("⚠️ needs confirmation")
        return " · ".join(parts)

    if tool_name == "log_consumption":
        count = content.get("count", 0)
        warnings = content.get("calorie_warnings", [])
        total = content.get("new_total_calories", 0)
        result = f"Saved {count} item(s)"
        if count == 0:
            result = "⚠️ Nothing was saved (entries may be malformed)"
        if total:
            result += f" · total today ~{int(total)} kcal"
        if warnings:
            result += f" · {warnings[0][:80]}"
        return result

    if tool_name == "get_daily_status":
        summary = content.get("summary", "")
        opts = len(content.get("logged_options", []))
        items = len(content.get("logged_items", []))
        return f"{summary} ({opts} full options, {items} individual items)"

    if tool_name in ("search_plan_options", "search_parsed_plan_items"):
        results = content if isinstance(content, list) else []
        if results:
            top = results[0]
            conf = top.get("confidence", 0)
            name = (top.get("option_text") or top.get("item_name") or "")[:40]
            return f"{len(results)} result(s) · best: \"{name}\" ({conf:.0f}%)"
        return "No results"

    if tool_name in ("correct_consumption", "delete_consumption"):
        return "✅ Done" if content.get("success") else "❌ Event not found"

    if tool_name == "build_advice_context":
        advice = content.get("advice", "")
        return advice[:150] if advice else "OK"

    return str(content)[:150]


def _parse_reasoning_steps(new_messages_json: bytes) -> List[ReasoningStep]:
    try:
        msgs = json.loads(new_messages_json)
    except Exception:
        return []

    # Map tool_call_id → tool-return part
    returns: dict = {}
    for m in msgs:
        if not isinstance(m, dict) or m.get("kind") != "request":
            continue
        for p in m.get("parts", []):
            if isinstance(p, dict) and p.get("part_kind") == "tool-return":
                cid = p.get("tool_call_id", "")
                returns[cid] = p

    steps: List[ReasoningStep] = []
    for m in msgs:
        if not isinstance(m, dict) or m.get("kind") != "response":
            continue
        for p in m.get("parts", []):
            if not isinstance(p, dict) or p.get("part_kind") != "tool-call":
                continue
            tool_name = p.get("tool_name", "")
            call_id = p.get("tool_call_id", "")

            raw_args = p.get("args", "{}")
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except Exception:
                    args = {}
            else:
                args = raw_args if isinstance(raw_args, dict) else {}

            ret = returns.get(call_id, {})
            ret_content = ret.get("content", {})

            icon, label = _TOOL_META.get(tool_name, ("🔧", tool_name))

            steps.append(ReasoningStep(
                tool_name=tool_name,
                icon=icon,
                label=label,
                args_summary=_args_summary(tool_name, args),
                result_summary=_result_summary(tool_name, ret_content),
            ))

    return steps


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

    # ── 2. Run agent ──────────────────────────────────────────────────────────
    try:
        result = await agent.run(
            request.message,
            message_history=history,
            deps=deps,
        )
        assistant_text = getattr(result, "output", None) or getattr(result, "data", "") or ""
        messages_json: bytes = result.all_messages_json()
        new_messages_json: bytes = result.new_messages_json()
    except Exception as exc:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=500, detail=f"Assistant error: {exc}")

    # ── 3. Persist session history and fire-and-forget memory extraction ──────
    await session_service.save_history(request.session_id, messages_json)
    asyncio.create_task(memory_service.extract_and_save(messages_json))

    reasoning_steps = _parse_reasoning_steps(new_messages_json)

    return AssistantResponse(
        assistant_text=assistant_text,
        session_id=request.session_id,
        reasoning_steps=reasoning_steps,
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
