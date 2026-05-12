"""Tests for option text parsing."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

from app.models.diet import DietOption
from app.services.parser_service import parse_option_text, _extract_quantity


def test_extract_gram_quantity():
    qty, unit = _extract_quantity("150 گرم مرغ")
    assert qty == 150.0
    assert unit == "g"


def test_extract_unit_quantity():
    qty, unit = _extract_quantity("2 عدد خرما")
    assert qty == 2.0
    assert unit == "unit"


def test_extract_cup():
    qty, unit = _extract_quantity("1 لیوان شیر")
    assert qty == 1.0
    assert unit == "cup"


def test_extract_fraction_half():
    qty, unit = _extract_quantity("نصف پرتقال")
    assert qty == 0.5


def test_parse_multi_item_option():
    opt = DietOption(
        section="Breakfast",
        option_no=1,
        option_text="2 عدد نان تست + 1 لیوان شیر + 2 عدد خرما",
    )
    items = parse_option_text(opt)
    assert len(items) >= 3


def test_parse_sets_section():
    opt = DietOption(section="Lunch", option_no=5, option_text="150 گرم مرغ + 1 کاسه سالاد")
    items = parse_option_text(opt)
    assert all(i.section == "Lunch" for i in items)
    assert all(i.option_no == 5 for i in items)
