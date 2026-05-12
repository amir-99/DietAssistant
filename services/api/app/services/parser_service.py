"""Parses free-text diet option strings into constituent food/portion items."""
from __future__ import annotations
import re
from typing import List, Tuple, Optional
from app.models.diet import DietOption, ParsedItem

# Common separators in diet option texts
SEPARATORS = re.compile(r"[+،,\n\r]+")

# Persian/Arabic digit normalization
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

# Quantity patterns (handles Persian and English)
QTY_PATTERNS = [
    (re.compile(r"(\d+[\.,]?\d*)\s*(گرم|gr|g)\b"), "g"),
    (re.compile(r"(\d+[\.,]?\d*)\s*(میلی\s*لیتر|ml|cc)\b"), "ml"),
    (re.compile(r"(\d+[\.,]?\d*)\s*(لیوان|فنجان|cup)\b"), "cup"),
    (re.compile(r"(\d+[\.,]?\d*)\s*(عدد|دانه|تکه|برش|واحد|unit|pcs?)\b"), "unit"),
    (re.compile(r"(\d+[\.,]?\d*)\s*(قاشق\s*(?:سوپ|غذا)?|tbsp|tsp|tablespoon)\b"), "tbsp"),
    (re.compile(r"(\d+[\.,]?\d*)\s*(قاشق\s*چای|tsp)\b"), "tsp"),
    (re.compile(r"نصف|half"), "0.5"),
    (re.compile(r"یک\s*چهارم|quarter|ربع"), "0.25"),
]

FRACTION_WORDS = {
    "نصف": 0.5, "half": 0.5,
    "یک چهارم": 0.25, "quarter": 0.25, "ربع": 0.25,
    "دو سوم": 0.667, "two thirds": 0.667,
    "یک سوم": 0.333, "one third": 0.333,
}


def _normalize_digits(text: str) -> str:
    return text.translate(PERSIAN_DIGITS)


def _extract_quantity(phrase: str) -> Tuple[Optional[float], str]:
    phrase_n = _normalize_digits(phrase)
    for frac_word, frac_val in FRACTION_WORDS.items():
        if frac_word in phrase_n.lower():
            return frac_val, "fraction"
    for pattern, unit in QTY_PATTERNS:
        if isinstance(unit, str) and unit not in ("g", "ml", "cup", "unit", "tbsp", "tsp"):
            continue
        m = pattern.search(phrase_n)
        if m and m.lastindex and m.lastindex >= 1:
            try:
                qty = float(m.group(1).replace(",", "."))
                return qty, unit
            except (ValueError, AttributeError):
                continue
    # Bare number at start
    m = re.match(r"^(\d+[\.,]?\d*)\s", phrase_n)
    if m:
        try:
            return float(m.group(1).replace(",", ".")), "unit"
        except ValueError:
            pass
    return None, ""


def parse_option_text(option: DietOption) -> List[ParsedItem]:
    """Split one option text into constituent items with best-effort quantity parsing."""
    text = _normalize_digits(option.option_text)
    parts = [p.strip() for p in SEPARATORS.split(text) if p.strip()]
    items: List[ParsedItem] = []

    for order, phrase in enumerate(parts, start=1):
        if len(phrase) < 2:
            continue
        qty_numeric, unit = _extract_quantity(phrase)
        qty_text = phrase  # preserve raw

        # Confidence heuristic: higher if we found a numeric quantity
        confidence = 0.7 if qty_numeric is not None else 0.4

        # Strip leading digits/units to get item name guess
        name_guess = re.sub(r"^\d+[\.,]?\d*\s*\w*\s*", "", phrase).strip()
        if not name_guess:
            name_guess = phrase

        items.append(ParsedItem(
            section=option.section,
            option_no=option.option_no,
            source_option_text=option.option_text,
            parsed_item_order=order,
            item_name_guess=name_guess,
            quantity_text=qty_text,
            quantity_numeric=qty_numeric,
            unit_guess=unit,
            parser_confidence=confidence,
            review_status="auto",
        ))

    return items


def parse_all_options(options: List[DietOption]) -> List[ParsedItem]:
    all_items: List[ParsedItem] = []
    for opt in options:
        all_items.extend(parse_option_text(opt))
    return all_items
