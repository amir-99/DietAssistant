from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date


def _coerce_int(v):
    """Coerce numeric values (including floats like 3.0) to int."""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


class ConsumptionEvent(BaseModel):
    event_id: str
    timestamp_local: str
    date_local: str
    raw_user_message: str
    log_type: str  # option | item | mixed | unregistered | correction
    section: Optional[str] = None
    option_no: Optional[int] = None
    source_option_text: Optional[str] = None
    item_name: Optional[str] = None
    consumed_qty_text: Optional[str] = None
    consumed_qty_numeric: Optional[float] = None
    consumed_unit: Optional[str] = None
    portion_fraction: Optional[float] = None
    confidence: Optional[float] = None
    status: str = "confirmed"  # confirmed | needs_review | corrected | deleted
    estimated_calories: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("option_no", mode="before")
    @classmethod
    def coerce_option_no(cls, v):
        return _coerce_int(v)


class ConsumptionEventCreate(BaseModel):
    log_type: str
    section: Optional[str] = None
    option_no: Optional[int] = None
    source_option_text: Optional[str] = None
    item_name: Optional[str] = None
    consumed_qty_text: Optional[str] = None
    consumed_qty_numeric: Optional[float] = None
    consumed_unit: Optional[str] = None
    portion_fraction: Optional[float] = None
    confidence: Optional[float] = None
    status: str = "confirmed"
    estimated_calories: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("option_no", mode="before")
    @classmethod
    def coerce_option_no(cls, v):
        return _coerce_int(v)


class LogRequest(BaseModel):
    entries: List[ConsumptionEventCreate]
    raw_user_message: str


class EventPatch(BaseModel):
    item_name: Optional[str] = None
    consumed_qty_text: Optional[str] = None
    consumed_qty_numeric: Optional[float] = None
    consumed_unit: Optional[str] = None
    option_no: Optional[int] = None
    section: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class DailyStatusItem(BaseModel):
    date_local: str
    status_type: str
    section: Optional[str] = None
    option_no: Optional[int] = None
    item_name: Optional[str] = None
    planned_qty_text: Optional[str] = None
    consumed_qty_text: Optional[str] = None
    consumed_qty_numeric: Optional[float] = None
    remaining_qty_numeric: Optional[float] = None
    completion_pct: Optional[float] = None
    confidence_note: Optional[str] = None


class DailyStatusResponse(BaseModel):
    date: str
    logged_options: List[ConsumptionEvent]
    logged_items: List[ConsumptionEvent]
    section_coverage: dict
    status_items: List[DailyStatusItem]
    summary: str


class ChatMessage(BaseModel):
    role: str
    content: str


class AssistantRequest(BaseModel):
    message: str
    session_id: str = "default"
    date_override: Optional[str] = None


class ReasoningStep(BaseModel):
    tool_name: str
    icon: str
    label: str
    args_summary: str
    result_summary: str


class AssistantResponse(BaseModel):
    assistant_text: str
    logged_entries: List[ConsumptionEvent] = []
    matched_options: List[dict] = []
    matched_items: List[dict] = []
    warnings: List[str] = []
    confirmation_requests: List[dict] = []
    status_preview: Optional[dict] = None
    session_id: str = "default"
    reasoning_steps: List[ReasoningStep] = []
