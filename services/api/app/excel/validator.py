"""Validates that an uploaded workbook matches the supported diet-plan format."""
from __future__ import annotations
import io
from typing import List, Tuple
import defusedxml.ElementTree  # noqa: F401 – patches xml.etree before openpyxl
import openpyxl

REQUIRED_SHEETS = ["All Sections", "Breakfast", "Lunch", "Dinner", "Snack 1", "Snack 2", "Snack 3", "Index"]
ALL_SECTIONS_COLS = {"Section", "Option No.", "Diet option (exact PDF text)"}
SECTION_COLS = {"Option No.", "Diet option (exact PDF text)"}
INDEX_COLS = {"Section", "Options Extracted"}


def _header_set(ws) -> set[str]:
    headers = set()
    for cell in ws[1]:
        if cell.value:
            headers.add(str(cell.value).strip())
    return headers


def validate_workbook(file_bytes: bytes) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as exc:
        return False, [f"Cannot open workbook: {exc}"]

    present = set(wb.sheetnames)
    missing = [s for s in REQUIRED_SHEETS if s not in present]
    if missing:
        errors.append(f"Missing sheets: {', '.join(missing)}")

    if "All Sections" in present:
        headers = _header_set(wb["All Sections"])
        missing_cols = ALL_SECTIONS_COLS - headers
        if missing_cols:
            errors.append(f"'All Sections' missing columns: {', '.join(missing_cols)}")

    for section in ["Breakfast", "Lunch", "Dinner", "Snack 1", "Snack 2", "Snack 3"]:
        if section in present:
            headers = _header_set(wb[section])
            missing_cols = SECTION_COLS - headers
            if missing_cols:
                errors.append(f"'{section}' missing columns: {', '.join(missing_cols)}")

    if "Index" in present:
        headers = _header_set(wb["Index"])
        missing_cols = INDEX_COLS - headers
        if missing_cols:
            errors.append(f"'Index' missing columns: {', '.join(missing_cols)}")

    wb.close()
    return len(errors) == 0, errors
