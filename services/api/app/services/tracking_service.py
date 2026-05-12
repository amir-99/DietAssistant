"""Tracking service: daily status calculation and consumption queries."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime, date
import pytz

from app.models.tracking import ConsumptionEvent, DailyStatusItem, DailyStatusResponse
from app.excel.reader import read_consumption_log
from app.models.diet import ParsedItem


def get_total_calories_today(events: List[ConsumptionEvent]) -> float:
    return sum(e.estimated_calories for e in events if e.estimated_calories is not None)


def _get_today(tz: str) -> str:
    return datetime.now(pytz.timezone(tz)).strftime("%Y-%m-%d")


def get_events(workbook_path: str, date_filter: Optional[str] = None) -> List[ConsumptionEvent]:
    raw = read_consumption_log(workbook_path)
    events = []
    for row in raw:
        if not row.get("event_id"):
            continue
        if row.get("status") == "deleted":
            continue
        ev = _row_to_event(row)
        if date_filter and ev.date_local != date_filter:
            continue
        events.append(ev)
    return events


def _row_to_event(row: dict) -> ConsumptionEvent:
    def _safe_float(v):
        try:
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def _safe_int(v):
        try:
            return int(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    return ConsumptionEvent(
        event_id=str(row.get("event_id", "")),
        timestamp_local=str(row.get("timestamp_local", "")),
        date_local=str(row.get("date_local", "")),
        raw_user_message=str(row.get("raw_user_message", "")),
        log_type=str(row.get("log_type", "item")),
        section=row.get("section") or None,
        option_no=_safe_int(row.get("option_no")),
        source_option_text=row.get("source_option_text") or None,
        item_name=row.get("item_name") or None,
        consumed_qty_text=row.get("consumed_qty_text") or None,
        consumed_qty_numeric=_safe_float(row.get("consumed_qty_numeric")),
        consumed_unit=row.get("consumed_unit") or None,
        portion_fraction=_safe_float(row.get("portion_fraction")),
        confidence=_safe_float(row.get("confidence")),
        status=str(row.get("status", "confirmed")),
        estimated_calories=_safe_float(row.get("estimated_calories")),
        notes=row.get("notes") or None,
    )


def get_daily_status(
    workbook_path: str,
    target_date: str,
    parsed_items: List[ParsedItem],
    tz: str = "Asia/Tehran",
) -> DailyStatusResponse:
    events = get_events(workbook_path, date_filter=target_date)

    logged_options = [e for e in events if e.log_type == "option"]
    logged_items = [e for e in events if e.log_type in ("item", "mixed")]

    # Section coverage
    section_coverage: dict = {}
    for ev in events:
        if ev.section:
            section_coverage.setdefault(ev.section, {"options": 0, "items": 0})
            if ev.log_type == "option":
                section_coverage[ev.section]["options"] += 1
            else:
                section_coverage[ev.section]["items"] += 1

    # Build status items for deterministic item-level tracking
    status_items: List[DailyStatusItem] = []

    # For each logged item, try to find planned amount
    for ev in logged_items:
        planned_text = None
        remaining = None
        completion = None

        if ev.item_name:
            # Find matching parsed plan item
            for pi in parsed_items:
                if pi.item_name_guess.lower() in (ev.item_name or "").lower():
                    planned_text = pi.quantity_text
                    if pi.quantity_numeric and ev.consumed_qty_numeric:
                        remaining = max(pi.quantity_numeric - ev.consumed_qty_numeric, 0)
                        completion = min(ev.consumed_qty_numeric / pi.quantity_numeric * 100, 100)
                    break

        status_items.append(DailyStatusItem(
            date_local=target_date,
            status_type="item",
            section=ev.section,
            option_no=ev.option_no,
            item_name=ev.item_name,
            planned_qty_text=planned_text,
            consumed_qty_text=ev.consumed_qty_text,
            consumed_qty_numeric=ev.consumed_qty_numeric,
            remaining_qty_numeric=remaining,
            completion_pct=completion,
            confidence_note="calculated" if completion is not None else "no_plan_quantity",
        ))

    # Section summaries
    for section, counts in section_coverage.items():
        status_items.append(DailyStatusItem(
            date_local=target_date,
            status_type="section_summary",
            section=section,
            confidence_note=f"{counts['options']} option(s), {counts['items']} individual item(s) logged",
        ))

    # Build summary text
    summary_parts = []
    if logged_options:
        summary_parts.append(f"Logged {len(logged_options)} complete option(s).")
    if logged_items:
        summary_parts.append(f"Logged {len(logged_items)} individual item(s).")
    if not events:
        summary_parts.append("No food logged today yet.")
    summary = " ".join(summary_parts)

    return DailyStatusResponse(
        date=target_date,
        logged_options=logged_options,
        logged_items=logged_items,
        section_coverage=section_coverage,
        status_items=status_items,
        summary=summary,
    )
