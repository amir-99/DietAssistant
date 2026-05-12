"""Tests for fuzzy matching logic."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

from app.models.diet import DietOption
from app.services.matching_service import (
    match_options,
    parse_section_from_text,
    parse_option_number_from_text,
)

SAMPLE_OPTIONS = [
    DietOption(section="Breakfast", option_no=1, option_text="نان تست با پنیر و خرما"),
    DietOption(section="Breakfast", option_no=2, option_text="شیر و جو با عسل"),
    DietOption(section="Lunch", option_no=1, option_text="برنج با مرغ و سالاد"),
    DietOption(section="Lunch", option_no=2, option_text="ماهی با سبزیجات"),
]


def test_exact_option_number_match():
    results = match_options("I ate breakfast option 1", SAMPLE_OPTIONS)
    assert any(r.option.option_no == 1 and r.option.section == "Breakfast" for r in results)
    assert results[0].confidence >= 90


def test_section_filter():
    results = match_options("option 2", SAMPLE_OPTIONS, section_filter="Lunch")
    assert all(r.option.section == "Lunch" for r in results)


def test_parse_section_breakfast():
    assert parse_section_from_text("I had breakfast option 3") == "Breakfast"
    assert parse_section_from_text("صبحانه گزینه ۳") == "Breakfast"


def test_parse_section_lunch():
    assert parse_section_from_text("lunch today was great") == "Lunch"


def test_parse_option_number():
    assert parse_option_number_from_text("I ate option 7") == 7
    assert parse_option_number_from_text("گزینه 3 را خوردم") == 3


def test_no_option_number():
    assert parse_option_number_from_text("I had some rice and chicken") is None
