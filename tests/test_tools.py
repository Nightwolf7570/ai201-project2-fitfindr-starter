"""
Failure-mode tests for the three FitFindr tools.

Per planning.md, each tool has a specific failure mode it must handle without
raising. These tests deliberately trigger each one.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_empty_wardrobe


def test_search_listings_returns_empty_list_when_no_match():
    """search_listings must return [] (not raise) when nothing matches."""
    results = search_listings("designer ballgown unicorn", size="XXS", max_price=5)
    assert results == []


def test_suggest_outfit_handles_empty_wardrobe():
    """suggest_outfit must return a useful non-empty string when wardrobe is empty."""
    fake_item = {
        "title": "Vintage Band Tee",
        "category": "tops",
        "colors": ["black"],
        "style_tags": ["vintage", "graphic tee"],
    }
    result = suggest_outfit(fake_item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_create_fit_card_handles_empty_outfit():
    """create_fit_card must return an error string (not raise) when outfit is empty."""
    fake_item = {
        "title": "Vintage Band Tee",
        "price": 22.0,
        "platform": "depop",
    }
    result = create_fit_card("", fake_item)
    assert isinstance(result, str)
    assert "outfit" in result.lower()
