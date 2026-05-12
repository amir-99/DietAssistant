"""Tests for workbook validation."""
import io
import pytest
import openpyxl


def _make_wb(sheets: dict) -> bytes:
    wb = openpyxl.Workbook()
    first = True
    for name, headers in sheets.items():
        if first:
            ws = wb.active
            ws.title = name
            first = False
        else:
            ws = wb.create_sheet(name)
        ws.append(headers)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _full_wb() -> bytes:
    sheets = {
        "All Sections": ["Section", "Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Breakfast": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Lunch": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Dinner": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Snack 1": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Snack 2": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Snack 3": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Index": ["Section", "Options Extracted", "PDF Page(s)"],
    }
    return _make_wb(sheets)


def test_valid_workbook():
    from services.api.app.excel.validator import validate_workbook
    valid, errors = validate_workbook(_full_wb())
    assert valid
    assert errors == []


def test_missing_sheet():
    sheets = {
        "All Sections": ["Section", "Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Breakfast": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        # Missing Lunch, Dinner, Snacks, Index
    }
    from services.api.app.excel.validator import validate_workbook
    valid, errors = validate_workbook(_make_wb(sheets))
    assert not valid
    assert any("Lunch" in e for e in errors)


def test_missing_column():
    sheets = {
        "All Sections": ["Section", "Option No."],  # Missing "Diet option (exact PDF text)"
        "Breakfast": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Lunch": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Dinner": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Snack 1": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Snack 2": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Snack 3": ["Option No.", "Diet option (exact PDF text)", "PDF Page"],
        "Index": ["Section", "Options Extracted", "PDF Page(s)"],
    }
    from services.api.app.excel.validator import validate_workbook
    valid, errors = validate_workbook(_make_wb(sheets))
    assert not valid
    assert any("Diet option" in e for e in errors)
