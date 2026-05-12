from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

VALID_SECTIONS = ["Breakfast", "Lunch", "Dinner", "Snack 1", "Snack 2", "Snack 3"]


class DietOption(BaseModel):
    section: str
    option_no: int
    option_text: str
    pdf_page: Optional[str] = None


class ParsedItem(BaseModel):
    id: Optional[int] = None
    section: str
    option_no: int
    source_option_text: str
    parsed_item_order: int
    item_name_guess: str
    quantity_text: str = ""
    quantity_numeric: Optional[float] = None
    unit_guess: str = ""
    parser_confidence: float = 0.0
    review_status: str = "auto"


class PlanSectionSummary(BaseModel):
    section: str
    option_count: int
    pdf_pages: str = ""


class PlanInfo(BaseModel):
    sections: list[PlanSectionSummary]
    total_options: int
    workbook_active: bool


class SearchResult(BaseModel):
    option: DietOption
    confidence: float
    match_type: str


class ParsedItemSearchResult(BaseModel):
    item: ParsedItem
    confidence: float
