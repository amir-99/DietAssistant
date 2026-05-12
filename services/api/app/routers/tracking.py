from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime
import pytz

from app.config import get_settings, Settings
from app.models.tracking import EventPatch, ConsumptionEventCreate, LogRequest
from app.services import tracking_service, plan_service
from app.excel import writer as excel_writer

router = APIRouter(prefix="/tracking", tags=["tracking"])


def _require_workbook(settings: Settings = Depends(get_settings)):
    if not settings.workbook_path.exists():
        raise HTTPException(status_code=404, detail="No active diet plan. Upload a workbook first.")
    return settings


@router.post("/log")
async def log_consumption(
    request: LogRequest,
    settings: Settings = Depends(_require_workbook),
):
    today = datetime.now(pytz.timezone(settings.tz)).strftime("%Y-%m-%d")
    written_ids = []
    for entry in request.entries:
        eid = excel_writer.write_consumption_event(
            str(settings.workbook_path),
            entry,
            request.raw_user_message,
            today,
            tz=settings.tz,
        )
        written_ids.append(eid)
    return {"written_event_ids": written_ids, "count": len(written_ids)}


@router.get("/day/{date}")
async def get_day_tracking(date: str, settings: Settings = Depends(_require_workbook)):
    parsed_items = plan_service.get_parsed_items(str(settings.workbook_path))
    status = tracking_service.get_daily_status(
        str(settings.workbook_path), date, parsed_items, tz=settings.tz
    )
    return status.model_dump()


@router.get("/events")
async def get_events(
    date: Optional[str] = None,
    settings: Settings = Depends(_require_workbook),
):
    events = tracking_service.get_events(str(settings.workbook_path), date_filter=date)
    return {"events": [e.model_dump() for e in events], "count": len(events)}


@router.patch("/events/{event_id}")
async def patch_event(
    event_id: str,
    patch: EventPatch,
    settings: Settings = Depends(_require_workbook),
):
    ok = excel_writer.patch_consumption_event(str(settings.workbook_path), event_id, patch)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found.")
    return {"success": True, "event_id": event_id}


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    settings: Settings = Depends(_require_workbook),
):
    ok = excel_writer.delete_consumption_event(str(settings.workbook_path), event_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found.")
    return {"success": True, "event_id": event_id}
