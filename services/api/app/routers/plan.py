from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from fastapi.responses import StreamingResponse
import io
from typing import Optional

from app.config import get_settings, Settings
from app.excel.validator import validate_workbook
from app.excel.template import generate_template
from app.services import plan_service, plan_meta_service
from app.models.diet import DietOption, PlanInfo

router = APIRouter(prefix="/plan", tags=["plan"])


def _require_workbook(settings: Settings = Depends(get_settings)):
    if not settings.workbook_path.exists():
        raise HTTPException(status_code=404, detail="No active diet plan workbook found. Please upload one first.")
    return settings


@router.post("/upload")
async def upload_plan(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are accepted.")

    contents = await file.read()
    valid, errors = validate_workbook(contents)
    if not valid:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    plan_service.activate_workbook(
        contents,
        str(settings.workbook_path),
        str(settings.backup_dir),
    )
    return {"status": "activated", "message": "Diet plan uploaded and activated successfully."}


@router.get("/template")
async def download_template():
    data = generate_template()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=diet_plan_template.xlsx"},
    )


@router.get("/current", response_model=PlanInfo)
async def get_current_plan(settings: Settings = Depends(_require_workbook)):
    return plan_service.get_plan_info(str(settings.workbook_path))


@router.get("/sections")
async def get_sections(settings: Settings = Depends(_require_workbook)):
    sections = plan_service.get_sections(str(settings.workbook_path))
    return {"sections": [s.model_dump() for s in sections]}


@router.get("/options")
async def get_options(
    section: Optional[str] = None,
    settings: Settings = Depends(_require_workbook),
):
    options = plan_service.get_options(str(settings.workbook_path))
    if section:
        options = [o for o in options if o.section.lower() == section.lower()]
    return {"options": [o.model_dump() for o in options], "count": len(options)}


@router.get("/options/{section}/{option_no}")
async def get_option(
    section: str,
    option_no: int,
    settings: Settings = Depends(_require_workbook),
):
    opt = plan_service.get_option(str(settings.workbook_path), section, option_no)
    if not opt:
        raise HTTPException(status_code=404, detail=f"Option {option_no} not found in section '{section}'.")
    parsed = [
        p for p in plan_service.get_parsed_items(str(settings.workbook_path))
        if p.section.lower() == section.lower() and p.option_no == option_no
    ]
    return {**opt.model_dump(), "parsed_items": [p.model_dump() for p in parsed]}


@router.get("/calorie-goal")
async def get_calorie_goal():
    """Get the stored daily calorie intake goal."""
    val = await plan_meta_service.get_plan_meta("daily_calorie_goal")
    return {"calorie_goal": int(val) if val else None}


@router.put("/calorie-goal")
async def set_calorie_goal(body: dict = Body(...)):
    """Set the daily calorie intake goal."""
    goal = body.get("calorie_goal")
    if goal is None or not isinstance(goal, (int, float)) or float(goal) <= 0:
        raise HTTPException(status_code=400, detail="calorie_goal must be a positive number")
    await plan_meta_service.set_plan_meta("daily_calorie_goal", str(int(goal)))
    return {"calorie_goal": int(goal)}


@router.post("/parse-options")
async def parse_options(settings: Settings = Depends(_require_workbook)):
    """Re-parse all options and store results in Parsed_Option_Items sheet."""
    from app.excel.reader import read_all_options
    from app.services.parser_service import parse_all_options
    from app.excel.writer import write_parsed_items

    plan_service.invalidate_cache()
    options = read_all_options(str(settings.workbook_path))
    items = parse_all_options(options)
    write_parsed_items(str(settings.workbook_path), items)
    plan_service.invalidate_cache()

    return {"parsed_item_count": len(items), "status": "complete"}


@router.get("/parsed-items")
async def get_parsed_items(settings: Settings = Depends(_require_workbook)):
    items = plan_service.get_parsed_items(str(settings.workbook_path))
    return {"items": [i.model_dump() for i in items], "count": len(items)}
