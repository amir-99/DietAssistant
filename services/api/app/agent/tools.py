"""Deterministic backend tools exposed to the PydanticAI agent."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import pytz

from app.models.diet import DietOption, ParsedItem, PlanSectionSummary
from app.models.tracking import ConsumptionEvent, ConsumptionEventCreate, EventPatch, DailyStatusResponse
from app.services import plan_service, tracking_service, matching_service
from app.excel import writer as excel_writer
from app.config import get_settings


@dataclass
class AgentDeps:
    workbook_path: str
    tz: str
    confidence_auto: int
    confidence_confirm: int
    date_override: Optional[str] = None
    memory_context: str = ""
    calorie_goal: int = 0
    total_calories_today: float = 0.0

    def today(self) -> str:
        if self.date_override:
            return self.date_override
        return datetime.now(pytz.timezone(self.tz)).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# Tool implementations (called by agent tool wrappers)
# ─────────────────────────────────────────────────────────────────────────────

def tool_get_plan_sections(deps: AgentDeps) -> List[dict]:
    sections = plan_service.get_sections(deps.workbook_path)
    return [s.model_dump() for s in sections]


def tool_search_plan_options(
    deps: AgentDeps,
    query: str,
    section_filter: Optional[str] = None,
    limit: int = 5,
) -> List[dict]:
    options = plan_service.get_options(deps.workbook_path)
    results = matching_service.match_options(query, options, section_filter=section_filter, limit=limit)
    return [
        {
            "section": r.option.section,
            "option_no": r.option.option_no,
            "option_text": r.option.option_text,
            "confidence": r.confidence,
            "match_type": r.match_type,
        }
        for r in results
    ]


def tool_get_plan_option(deps: AgentDeps, section: str, option_no: int) -> Optional[dict]:
    opt = plan_service.get_option(deps.workbook_path, section, option_no)
    if not opt:
        return None
    parsed = [
        p for p in plan_service.get_parsed_items(deps.workbook_path)
        if p.section.lower() == section.lower() and p.option_no == option_no
    ]
    return {
        "section": opt.section,
        "option_no": opt.option_no,
        "option_text": opt.option_text,
        "pdf_page": opt.pdf_page,
        "parsed_items": [p.model_dump() for p in parsed],
    }


def tool_search_parsed_plan_items(deps: AgentDeps, query: str, limit: int = 5) -> List[dict]:
    items = plan_service.get_parsed_items(deps.workbook_path)
    results = matching_service.match_parsed_items(query, items, limit=limit)
    return [
        {
            "item_name": r.item.item_name_guess,
            "section": r.item.section,
            "option_no": r.item.option_no,
            "quantity_text": r.item.quantity_text,
            "quantity_numeric": r.item.quantity_numeric,
            "unit": r.item.unit_guess,
            "confidence": r.confidence,
            "parser_confidence": r.item.parser_confidence,
        }
        for r in results
    ]


def tool_match_consumption_to_plan(
    deps: AgentDeps,
    user_text: str,
) -> dict:
    """Try to match free-form user consumption text against the plan."""
    options = plan_service.get_options(deps.workbook_path)
    parsed_items = plan_service.get_parsed_items(deps.workbook_path)

    # Detect section and option number from text
    section = matching_service.parse_section_from_text(user_text)
    option_no = matching_service.parse_option_number_from_text(user_text)

    matched_options = []
    matched_items = []
    ambiguity_flags = []

    # If section + option number are both identified
    if section and option_no:
        opt = plan_service.get_option(deps.workbook_path, section, option_no)
        if opt:
            matched_options.append({
                "section": opt.section,
                "option_no": opt.option_no,
                "option_text": opt.option_text,
                "confidence": 98.0,
                "match_type": "exact_section_option",
            })

    elif option_no:
        # Option number without section — search all
        for opt in options:
            if opt.option_no == option_no:
                matched_options.append({
                    "section": opt.section,
                    "option_no": opt.option_no,
                    "option_text": opt.option_text,
                    "confidence": 85.0,
                    "match_type": "option_no_no_section",
                })
        if len(matched_options) > 1:
            ambiguity_flags.append("Multiple sections have this option number. Please specify the section.")

    else:
        # Fuzzy search
        results = matching_service.match_options(user_text, options, section_filter=section, limit=3)
        for r in results:
            if r.confidence >= deps.confidence_confirm:
                matched_options.append({
                    "section": r.option.section,
                    "option_no": r.option.option_no,
                    "option_text": r.option.option_text,
                    "confidence": r.confidence,
                    "match_type": r.match_type,
                })

        # Also try item-level matching
        item_results = matching_service.match_parsed_items(user_text, parsed_items, limit=5)
        for r in item_results:
            if r.confidence >= deps.confidence_confirm:
                matched_items.append({
                    "item_name": r.item.item_name_guess,
                    "section": r.item.section,
                    "option_no": r.item.option_no,
                    "quantity_text": r.item.quantity_text,
                    "confidence": r.confidence,
                })

    needs_confirmation = any(
        m["confidence"] < deps.confidence_auto
        for m in (matched_options + matched_items)
    )

    return {
        "matched_options": matched_options,
        "matched_items": matched_items,
        "needs_confirmation": needs_confirmation,
        "ambiguity_flags": ambiguity_flags,
        "confidence_auto_threshold": deps.confidence_auto,
        "confidence_confirm_threshold": deps.confidence_confirm,
    }


import logging as _logging
_tool_logger = _logging.getLogger(__name__)


def _coerce_entry(raw) -> Optional[dict]:
    """Accept a dict, a JSON string, or a plain-text string; return a dict or None."""
    import json as _json
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("{"):
            try:
                return _json.loads(raw)
            except Exception:
                pass
        # Fallback: the LLM passed a plain-text description instead of a dict.
        # Salvage it as a generic item so nothing is silently dropped.
        if raw:
            _tool_logger.warning("log_consumption: entry was a plain string, salvaging as item_name: %r", raw[:80])
            return {"log_type": "item", "item_name": raw, "notes": f"Auto-salvaged from plain text: {raw[:120]}"}
    return None


def tool_log_consumption(
    deps: AgentDeps,
    entries: List[dict],
    raw_user_message: str,
) -> dict:
    """Write confirmed consumption entries to the Excel workbook.
    Each entry must have at least log_type ('option', 'item', or 'unregistered').
    Optional fields: section, option_no, source_option_text, item_name,
    consumed_qty_text, consumed_qty_numeric, consumed_unit, portion_fraction,
    confidence, estimated_calories, notes.
    """
    written_ids = []
    today = deps.today()
    newly_added_calories = 0.0

    for raw_entry in entries:
        entry_dict = _coerce_entry(raw_entry)
        if not entry_dict:
            continue
        try:
            entry = ConsumptionEventCreate(**entry_dict)
        except Exception:
            continue
        event_id = excel_writer.write_consumption_event(
            deps.workbook_path,
            entry,
            raw_user_message,
            today,
            tz=deps.tz,
        )
        written_ids.append(event_id)
        if entry.estimated_calories:
            newly_added_calories += entry.estimated_calories

    new_total = deps.total_calories_today + newly_added_calories
    calorie_warnings: List[str] = []

    if deps.calorie_goal > 0 and newly_added_calories > 0:
        if new_total > deps.calorie_goal:
            overage = new_total - deps.calorie_goal
            calorie_warnings.append(
                f"⚠️ Daily goal exceeded: adding this meal brings your total to ~{int(new_total)} kcal, "
                f"which is ~{int(overage)} kcal over your {deps.calorie_goal} kcal goal."
            )
        elif new_total >= deps.calorie_goal * 0.8:
            calorie_warnings.append(
                f"⚠️ Approaching daily goal: your total is now ~{int(new_total)} kcal "
                f"({int(new_total / deps.calorie_goal * 100)}% of your {deps.calorie_goal} kcal goal)."
            )

    return {
        "written_event_ids": written_ids,
        "date": today,
        "count": len(written_ids),
        "new_total_calories": round(new_total, 1),
        "calorie_warnings": calorie_warnings,
    }


def tool_get_daily_status(deps: AgentDeps, date: Optional[str] = None) -> dict:
    target = date or deps.today()
    parsed_items = plan_service.get_parsed_items(deps.workbook_path)
    status = tracking_service.get_daily_status(deps.workbook_path, target, parsed_items, tz=deps.tz)
    return status.model_dump()


def tool_correct_consumption(deps: AgentDeps, event_id: str, patch: dict) -> dict:
    patch_dict = _coerce_entry(patch) or {}
    ep = EventPatch(**patch_dict)
    ok = excel_writer.patch_consumption_event(deps.workbook_path, event_id, ep)
    return {"success": ok, "event_id": event_id}


def tool_delete_consumption(deps: AgentDeps, event_id: str) -> dict:
    ok = excel_writer.delete_consumption_event(deps.workbook_path, event_id)
    return {"success": ok, "event_id": event_id}


def tool_build_advice_context(deps: AgentDeps, date: Optional[str] = None) -> dict:
    target = date or deps.today()
    parsed_items = plan_service.get_parsed_items(deps.workbook_path)
    status = tracking_service.get_daily_status(deps.workbook_path, target, parsed_items, tz=deps.tz)

    sections_logged = list(status.section_coverage.keys())
    total_sections = ["Breakfast", "Lunch", "Dinner", "Snack 1", "Snack 2", "Snack 3"]
    unlogged_sections = [s for s in total_sections if s not in sections_logged]

    overages = []
    for si in status.status_items:
        if si.remaining_qty_numeric is not None and si.remaining_qty_numeric < 0:
            overages.append({
                "item": si.item_name,
                "overage": abs(si.remaining_qty_numeric),
                "unit": "",
            })

    return {
        "date": target,
        "summary": status.summary,
        "sections_with_activity": sections_logged,
        "sections_without_activity": unlogged_sections,
        "logged_option_count": len(status.logged_options),
        "logged_item_count": len(status.logged_items),
        "overages": overages,
        "advice": (
            f"Today you have logged {len(status.logged_options)} complete plan options and "
            f"{len(status.logged_items)} individual items. "
            + (f"Sections not yet logged: {', '.join(unlogged_sections)}. " if unlogged_sections else "All sections have activity. ")
            + ("Some items may be over the planned amount — please review." if overages else "No overages detected.")
        ),
    }
