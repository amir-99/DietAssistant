from fastapi import APIRouter
from pathlib import Path
from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    settings = get_settings()
    workbook_active = settings.workbook_path.exists()
    return {"status": "ready", "workbook_active": workbook_active}
