# FitFindr

A multi-tool AI agent that helps users find secondhand pieces and figure out how to wear them. Given a natural language query, FitFindr searches a mock listings dataset, suggests how to style the top result against the user's existing wardrobe, and generates a shareable outfit caption.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

Get a free Groq key at [console.groq.com](https://console.groq.com).

## Run

```bash
python app.py          # launch the Gradio UI
python agent.py        # run the CLI smoke test (happy path + no-results path)
pytest tests/          # run failure-mode tests
```

The Gradio UI prints its local URL on startup (usually `http://localhost:7860`).

---

## Tool Inventory

### 1. `search_listings(description, size, max_price) -> list[dict]`

**Purpose:** Filter and rank the 40 mock listings against a free-text description, optional size, and optional price ceiling. Returns the top 3 matches.

**Inputs:**
- `description` (str) — keyword phrase describing what the user wants (e.g. `"vintage graphic tee"`).
- `size` (str | None) — optional size filter, case-insensitive substring match against the listing's `size` field. So `"M"` matches `"M"`, `"S/M"`, and `"M/L"`.
- `max_price` (float | None) — optional upper price bound (inclusive).

**Returns:** A list of up to 3 listing dicts sorted by relevance score (highest first). Each dict contains `id, title, description, category, style_tags, size, condition, price, colors, brand, platform`. Returns `[]` if nothing matches — never raises.

### 2. `suggest_outfit(new_item, wardrobe) -> str`

**Purpose:** Ask the LLM how to style the new item using pieces from the user's existing wardrobe.

**Inputs:**
- `new_item` (dict) — one listing dict (the top result from `search_listings`).
- `wardrobe` (dict) — `{"items": [...]}` where each item has `name, category, colors, style_tags, notes`. May be empty.

**Returns:** A non-empty string with 1–2 outfit suggestions naming specific wardrobe pieces. If the wardrobe is empty, falls back to general styling advice for the new item. Never raises.

### 3. `create_fit_card(outfit, new_item) -> str`

**Purpose:** Generate a short, casual social-media-style caption (2–4 sentences) describing the outfit. Uses a higher LLM temperature so the output varies across calls.

**Inputs:**
- `outfit` (str) — the suggestion string from `suggest_outfit`.
- `new_item` (dict) — the listing dict for the thrifted item.

**Returns:** A 2–4 sentence caption naturally mentioning the item, price, and platform once each. If `outfit` is empty/whitespace, returns the error string `"Can't generate a fit card without an outfit suggestion."` — never raises.

---

## How the Planning Loop Works

`run_agent(query, wardrobe)` (in `agent.py`) is a single linear loop with **one conditional branch**. The conditional is what makes this a planning loop instead of a hard-coded pipeline: the agent does not unconditionally call all three tools.

1. **Parse** the query with regex. Pulls `description`, `size`, and `max_price` out of free text. Result is written to `session["parsed"]`.
2. **Search** by calling `search_listings(description, size, max_price)`. Result is written to `session["search_results"]`.
3. **Branch on empty results.** If `search_results == []`:
   - Set `session["error"]` to a helpful message.
   - Return the session immediately.
   - `suggest_outfit` and `create_fit_card` are **never called** with empty input.
4. **Select top result.** `session["selected_item"] = session["search_results"][0]`.
5. **Suggest outfit.** Call `suggest_outfit(selected_item, wardrobe)`; store in `session["outfit_suggestion"]`.
6. **Create fit card.** Call `create_fit_card(outfit_suggestion, selected_item)`; store in `session["fit_card"]`.
7. **Return** the session.

The conditional in step 3 is the only point where the loop's behavior changes based on tool output. Without it, calling `suggest_outfit({}, wardrobe)` would either crash or produce nonsense for the LLM.

---

## State Management

Each call to `run_agent()` creates a fresh `session` dict via `_new_session()`. Every tool's output is written into a specific field; the next tool reads from that field. Nothing is global — re-running with a different query gives an independent session.

| Field | Set by | Read by |
|---|---|---|
| `query` | caller | parser (step 1) |
| `parsed` | step 1 | step 2 |
| `search_results` | step 2 | branch (step 3), step 4 |
| `selected_item` | step 4 | steps 5 + 6 |
| `wardrobe` | caller | step 5 |
| `outfit_suggestion` | step 5 | step 6 |
| `fit_card` | step 6 | UI / caller |
| `error` | step 3 (only on empty search) | UI / caller |

Information flows one direction: parser → search → outfit → fit card. The session dict is the only shared state — tools themselves are stateless.

---

## Error Handling

Each tool handles its own failure mode without raising. The agent and UI react to those signals.

| Tool | Failure mode | Tool behavior | Agent / UI response |
|---|---|---|---|
| `search_listings` | No results match | Returns `[]` | Agent sets `session["error"]`, returns early. UI shows the error in the 🛍️ panel; the other two panels are empty. |
| `suggest_outfit` | Wardrobe is empty | LLM is asked for **general** styling advice (no specific pieces to refer to) | Agent receives a normal non-empty string and continues to fit-card. |
| `create_fit_card` | `outfit` is empty/whitespace | Returns the string `"Can't generate a fit card without an outfit suggestion."` | UI displays the error string in the ✨ panel. No exception, no crash. |

All three LLM-backed tools also catch unexpected exceptions (e.g. network/API errors) and return a polite fallback string rather than crashing the agent.

### Concrete example: empty-search recovery

Running:

```bash
python -c "from agent import run_agent; from utils.data_loader import get_example_wardrobe; \
    s = run_agent('designer ballgown size XXS under \$5', get_example_wardrobe()); \
    print('error:', s['error']); print('outfit:', s['outfit_suggestion']); print('fit_card:', s['fit_card'])"
```

Output:

```
error: No thriftable items found matching your query. Try different keywords or relax the price/size filters.
outfit: None
fit_card: None
```

Notice `outfit` and `fit_card` are both `None` — the agent successfully refused to call downstream tools with empty input.

---

## Spec Reflection

**One way the spec helped:** Writing the planning loop in `planning.md` as 7 numbered steps with an explicit empty-search branch made the actual code in `run_agent()` almost mechanical to translate. Without the branch being called out in the spec, the natural temptation would have been to call all three tools in sequence and try to "salvage" the empty case downstream.

**One way the implementation diverged from the spec:** The spec example shows `search_listings` returning *all* matches sorted by relevance. The spec's planning section also said "top 3 most relevant results." We capped at 3 in code because the agent only ever uses `search_results[0]` — returning more would be unused data. If a future stretch feature surfaces a "show more matches" panel, the cap should be raised.

---

## AI Usage

**Instance 1 — Implementing `search_listings`.** I gave Claude the Tool 1 block from `planning.md` (description, inputs, return, failure mode) plus the existing docstring from `tools.py`, and asked for an implementation that used `load_listings()` from the data loader. The first draft scored only on title + description, which would have missed listings where the match lives in `style_tags` (e.g. "y2k" or "grunge" as tags). I overrode it to score across `title + description + style_tags + colors + category`, and added a tokenizer that drops single-character tokens so noise words don't count.

**Instance 2 — Implementing the planning loop.** I gave Claude the Planning Loop section, the State Management section, and the ASCII architecture diagram from `planning.md`, and asked for `run_agent()`. The generated code was structurally correct but used `if len(session["search_results"]) == 0:` and called `suggest_outfit` even when `selected_item` was `None`. I rewrote the branch as `if not session["search_results"]: ... return session` to make the early-return obvious, and added the `selected_item` assignment as its own step so the field is never accessed before being written.

---

## Project Structure

```
ai201-project2-fitfindr-starter/
├── agent.py              # run_agent() planning loop + CLI smoke test
├── app.py                # Gradio UI
├── tools.py              # search_listings, suggest_outfit, create_fit_card
├── planning.md           # spec written before implementation
├── tests/
│   └── test_tools.py     # failure-mode tests
├── data/
│   ├── listings.json
│   └── wardrobe_schema.json
└── utils/
    └── data_loader.py
```
