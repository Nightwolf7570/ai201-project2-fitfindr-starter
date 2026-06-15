"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Usage:
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ── query parsing (regex) ─────────────────────────────────────────────────────

_PRICE_RE = re.compile(r"(?:under|below|<=?|less than|max(?:imum)? of|cheaper than)\s*\$?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
_PRICE_FALLBACK_RE = re.compile(r"\$\s*(\d+(?:\.\d+)?)")
_SIZE_RE = re.compile(r"\bsize\s+([a-zA-Z0-9/]+)\b", re.IGNORECASE)
_SIZE_SHORTHAND_RE = re.compile(r"\b(XXS|XS|S|M|L|XL|XXL)\b")

# Phrases to strip from the query before treating the rest as the description
_STRIP_PATTERNS = [
    _PRICE_RE,
    _PRICE_FALLBACK_RE,
    _SIZE_RE,
    re.compile(r"\b(i'm|im|i am|looking for|find me|i want|i need|please|can you|show me)\b", re.IGNORECASE),
    re.compile(r"[,.!?]"),
]


def _parse_query(query: str) -> dict:
    """Pull description, size, max_price out of a free-text query."""
    max_price = None
    m = _PRICE_RE.search(query)
    if m:
        max_price = float(m.group(1))
    else:
        m = _PRICE_FALLBACK_RE.search(query)
        if m:
            max_price = float(m.group(1))

    size = None
    m = _SIZE_RE.search(query)
    if m:
        size = m.group(1).upper()
    else:
        m = _SIZE_SHORTHAND_RE.search(query)
        if m:
            size = m.group(1).upper()

    description = query
    for pat in _STRIP_PATTERNS:
        description = pat.sub(" ", description)
    description = re.sub(r"\s+", " ", description).strip()

    return {"description": description, "size": size, "max_price": max_price}


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    session = _new_session(query, wardrobe)

    # Step 1: parse the query
    session["parsed"] = _parse_query(query)
    p = session["parsed"]

    # Step 2: search
    session["search_results"] = search_listings(
        p["description"], size=p["size"], max_price=p["max_price"]
    )

    # Step 3: branch on empty results
    if not session["search_results"]:
        session["error"] = (
            "No thriftable items found matching your query. "
            "Try different keywords or relax the price/size filters."
        )
        return session

    # Step 4: select top result
    session["selected_item"] = session["search_results"][0]

    # Step 5: suggest an outfit
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )

    # Step 6: create the fit card
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Parsed: {session['parsed']}")
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Parsed: {session2['parsed']}")
    print(f"Error message: {session2['error']}")
    print(f"Outfit suggestion (should be None): {session2['outfit_suggestion']}")
    print(f"Fit card (should be None): {session2['fit_card']}")
