"""High-level plan management: load, cache, parse, and query the active workbook."""
from __future__ import annotations
from functools import lru_cache
from typing import List, Optional
from pathlib import Path

from app.models.diet import DietOption, ParsedItem, PlanSectionSummary, PlanInfo
from app.excel.reader import read_all_options, read_plan_sections, read_parsed_items
from app.excel.writer import ensure_tracking_sheets, write_parsed_items
from app.services.parser_service import parse_all_options


_options_cache: Optional[List[DietOption]] = None
_parsed_cache: Optional[List[ParsedItem]] = None
_sections_cache: Optional[List[PlanSectionSummary]] = None


def invalidate_cache() -> None:
    global _options_cache, _parsed_cache, _sections_cache
    _options_cache = None
    _parsed_cache = None
    _sections_cache = None


def get_plan_info(workbook_path: str) -> PlanInfo:
    sections = get_sections(workbook_path)
    options = get_options(workbook_path)
    return PlanInfo(
        sections=sections,
        total_options=len(options),
        workbook_active=Path(workbook_path).exists(),
    )


def get_sections(workbook_path: str) -> List[PlanSectionSummary]:
    global _sections_cache
    if _sections_cache is None:
        _sections_cache = read_plan_sections(workbook_path)
    return _sections_cache


def get_options(workbook_path: str) -> List[DietOption]:
    global _options_cache
    if _options_cache is None:
        _options_cache = read_all_options(workbook_path)
    return _options_cache


def get_parsed_items(workbook_path: str) -> List[ParsedItem]:
    global _parsed_cache
    if _parsed_cache is None:
        # Try reading from workbook first
        items = read_parsed_items(workbook_path)
        if not items:
            # Parse from options
            options = get_options(workbook_path)
            items = parse_all_options(options)
            write_parsed_items(workbook_path, items)
        _parsed_cache = items
    return _parsed_cache


def get_option(workbook_path: str, section: str, option_no: int) -> Optional[DietOption]:
    options = get_options(workbook_path)
    for opt in options:
        if opt.section.lower() == section.lower() and opt.option_no == option_no:
            return opt
    return None


def activate_workbook(src_bytes: bytes, workbook_path: str, backup_dir: str) -> None:
    from app.excel.writer import backup_workbook
    import shutil, tempfile
    from pathlib import Path

    active_path = Path(workbook_path)
    active_path.parent.mkdir(parents=True, exist_ok=True)

    # Backup existing before overwrite
    if active_path.exists():
        backup_workbook(workbook_path, backup_dir)

    # Write new workbook
    active_path.write_bytes(src_bytes)

    # Ensure tracking sheets exist
    ensure_tracking_sheets(workbook_path)

    # Invalidate caches
    invalidate_cache()

    # Parse options and store
    options = read_all_options(workbook_path)
    items = parse_all_options(options)
    write_parsed_items(workbook_path, items)
