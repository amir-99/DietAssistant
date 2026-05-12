"""Fuzzy matching for diet options and parsed items."""
from __future__ import annotations
import re
from typing import List, Optional
from rapidfuzz import fuzz, process

from app.models.diet import DietOption, ParsedItem, SearchResult, ParsedItemSearchResult

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _normalize(text: str) -> str:
    t = text.translate(PERSIAN_DIGITS).lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


def match_options(
    query: str,
    options: List[DietOption],
    section_filter: Optional[str] = None,
    limit: int = 5,
) -> List[SearchResult]:
    if section_filter:
        pool = [o for o in options if o.section.lower() == section_filter.lower()]
    else:
        pool = options

    if not pool:
        return []

    # Check for "section option N" pattern
    section_opt_match = re.search(
        r"(?:breakfast|lunch|dinner|snack\s*\d|صبحانه|ناهار|شام|میان\s*وعده)\s+"
        r"(?:option|گزینه|آپشن)?\s*#?(\d+)",
        query.lower(),
    )

    if not section_opt_match:
        # Also try Persian-style
        section_opt_match = re.search(r"گزینه\s+(\d+)", query)

    results: List[SearchResult] = []

    # Exact option number reference check
    opt_no_match = re.search(r"(?:option|گزینه|آپشن)\s*#?(\d+)", query.lower())
    if opt_no_match:
        target_no = int(opt_no_match.group(1))
        for opt in pool:
            if opt.option_no == target_no:
                results.append(SearchResult(option=opt, confidence=95.0, match_type="exact_option_no"))
        if results:
            return results

    # Fuzzy text matching
    norm_query = _normalize(query)
    candidates = [(o, _normalize(o.option_text), i) for i, o in enumerate(pool)]
    scored: List[SearchResult] = []
    for opt, norm_text, _ in candidates:
        score = fuzz.partial_ratio(norm_query, norm_text)
        token_score = fuzz.token_set_ratio(norm_query, norm_text)
        best = max(score, token_score)
        if best > 40:
            scored.append(SearchResult(option=opt, confidence=float(best), match_type="fuzzy"))

    scored.sort(key=lambda r: r.confidence, reverse=True)
    return scored[:limit]


def match_parsed_items(
    query: str,
    items: List[ParsedItem],
    limit: int = 5,
) -> List[ParsedItemSearchResult]:
    if not items:
        return []
    norm_query = _normalize(query)
    scored: List[ParsedItemSearchResult] = []
    for item in items:
        name_score = fuzz.partial_ratio(norm_query, _normalize(item.item_name_guess))
        text_score = fuzz.token_set_ratio(norm_query, _normalize(item.quantity_text))
        best = max(name_score, text_score)
        if best > 50:
            scored.append(ParsedItemSearchResult(item=item, confidence=float(best)))
    scored.sort(key=lambda r: r.confidence, reverse=True)
    return scored[:limit]


def parse_section_from_text(text: str) -> Optional[str]:
    """Detect a section name mentioned in a user message."""
    lowered = text.lower()
    mapping = {
        "breakfast": "Breakfast", "صبحانه": "Breakfast",
        "lunch": "Lunch", "ناهار": "Lunch",
        "dinner": "Dinner", "شام": "Dinner",
        "snack 1": "Snack 1", "میان وعده ۱": "Snack 1", "میان وعده 1": "Snack 1",
        "snack 2": "Snack 2", "میان وعده ۲": "Snack 2", "میان وعده 2": "Snack 2",
        "snack 3": "Snack 3", "میان وعده ۳": "Snack 3", "میان وعده 3": "Snack 3",
        "snack": "Snack 1",
    }
    for keyword, section in mapping.items():
        if keyword in lowered:
            return section
    return None


def parse_option_number_from_text(text: str) -> Optional[int]:
    m = re.search(r"(?:option|گزینه|آپشن|شماره)\s*#?(\d+)", text.lower())
    if m:
        return int(m.group(1))
    m = re.search(r"#(\d+)", text)
    if m:
        return int(m.group(1))
    return None
