"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  -> list[dict]
    suggest_outfit(new_item, wardrobe)              -> str
    create_fit_card(outfit, new_item)               -> str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

_MODEL = "llama-3.3-70b-versatile"
_TOP_N = 3


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 1}


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    listings = load_listings()
    query_tokens = _tokenize(description)

    results = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None and size.lower() not in item["size"].lower():
            continue

        haystack = " ".join([
            item["title"],
            item["description"],
            " ".join(item["style_tags"]),
            " ".join(item["colors"]),
            item["category"],
        ])
        item_tokens = _tokenize(haystack)
        score = len(query_tokens & item_tokens)
        if score == 0:
            continue
        results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in results[:_TOP_N]]


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    items = wardrobe.get("items", []) if wardrobe else []
    new_summary = f'{new_item.get("title", "the new piece")} ({new_item.get("category", "?")}, colors: {", ".join(new_item.get("colors", [])) or "n/a"}, tags: {", ".join(new_item.get("style_tags", [])) or "n/a"})'

    if not items:
        prompt = (
            f"A user just found this secondhand piece: {new_summary}.\n"
            f"They have not entered their wardrobe yet. Give 2 short, concrete "
            f"styling ideas: name kinds of pieces (e.g. 'wide-leg jeans', "
            f"'black combat boots') that pair well, the overall vibe, and one "
            f"styling tip. Keep it under 120 words."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {it['name']} ({it['category']}, colors: {', '.join(it.get('colors', []))})"
            for it in items
        )
        prompt = (
            f"A user found this secondhand piece: {new_summary}.\n\n"
            f"Here is their existing wardrobe:\n{wardrobe_lines}\n\n"
            f"Suggest 1-2 complete outfit combinations using the new piece "
            f"plus specific pieces from the wardrobe (refer to them by name). "
            f"For each outfit include a one-line styling tip. Keep it under 150 words."
        )

    try:
        client = _get_groq_client()
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        text = resp.choices[0].message.content.strip()
        if not text:
            return "Couldn't generate an outfit suggestion right now. Try again."
        return text
    except Exception as e:
        return f"Outfit suggestion unavailable ({type(e).__name__}). Try again in a moment."


def create_fit_card(outfit: str, new_item: dict) -> str:
    if not outfit or not outfit.strip():
        return "Can't generate a fit card without an outfit suggestion."

    title = new_item.get("title", "this piece")
    price = new_item.get("price")
    platform = new_item.get("platform", "online")
    price_str = f"${price:g}" if isinstance(price, (int, float)) else "a steal"

    prompt = (
        f"Write a 2-4 sentence Instagram/TikTok caption for an outfit-of-the-day post.\n"
        f"The user just thrifted: {title} for {price_str} on {platform}.\n"
        f"The outfit they styled it with: {outfit}\n\n"
        f"Style guidelines:\n"
        f"- Sound casual and authentic, like a real OOTD post, not a product description\n"
        f"- Mention the item, price, and platform naturally (each once)\n"
        f"- Capture the outfit vibe in specific terms\n"
        f"- Lowercase is okay; an emoji or two is okay\n"
        f"- No hashtag spam"
    )

    try:
        client = _get_groq_client()
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
        )
        text = resp.choices[0].message.content.strip()
        if not text:
            return "Couldn't generate a fit card right now. Try again."
        return text
    except Exception as e:
        return f"Fit card unavailable ({type(e).__name__}). Try again in a moment."
