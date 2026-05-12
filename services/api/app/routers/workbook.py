from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from app.config import get_settings, Settings

router = APIRouter(prefix="/workbook", tags=["workbook"])


def _require_workbook(settings: Settings = Depends(get_settings)):
    if not settings.workbook_path.exists():
        raise HTTPException(status_code=404, detail="No active workbook found.")
    return settings


@router.get("/download")
async def download_workbook(settings: Settings = Depends(_require_workbook)):
    return FileResponse(
        path=str(settings.workbook_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="diet_plan_with_tracking.xlsx",
    )
