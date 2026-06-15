# FitFindr — [planning.md](http://planning.md)

> Complete this document before writing any implementation code. Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be. Your planning.md will be reviewed as part of your submission. Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields. You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**&lt;!-- Describe what this tool does in 1–2 sentences --&gt; It filters the mock listings dataset by a description based on the user query and additional input filters like size and max price. The tool returns the top 3 most relevant results from the mock listings dataset.

**Input parameters:**&lt;!-- List each parameter, its type, and what it represents --&gt;

- `description` (str): phrase describing what the user wants from their query
- `size` (str): size of clothing the user wants based on keyword matching on user query like "M"
- `max_price` (float): upper bound price that user wants to pay for the item

**What it returns:**&lt;!-- Describe the return value — what fields does a result contain? --&gt; returns the top 3 most relevant results from the mock database based on the input filters

**What happens if it fails or returns nothing:**&lt;!-- What should the agent do if no listings match? --&gt; It should return an error message stating that no items were found that matched the filters, consider changing them.

---

### Tool 2: suggest_outfit

**What it does:**&lt;!-- Describe what this tool does in 1–2 sentences --&gt; Takes the new item the user found the user's existing wardrobe and uses the LLM to find ways to style the new item with existing wardrobe pices.

**Input parameters:**&lt;!-- List each parameter, its type, and what it represents --&gt;

- `new_item` (dict): Top result from search_results
- `wardrobe` (dict): List of existing wardrobe items

**What it returns:**&lt;!-- Describe the return value --&gt; Returns a string with outfit suggestions and names specific piece from wardrobe by name

**What happens if it fails or returns nothing:**&lt;!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? --&gt; It still returns a useful message by asking the LLM to pair the new item for general pairing advice even outside the wardrobe

---

### Tool 3: create_fit_card

**What it does:**&lt;!-- Describe what this tool does in 1–2 sentences --&gt; It generates a short caption describing the outfit based on the outfit suggested from the suggest_outfit tool call result

**Input parameters:**&lt;!-- List each parameter, its type, and what it represents --&gt;

- `outfit` (...): The result of tool 2: suggest_outfit string

**What it returns:**&lt;!-- Describe the return value --&gt; It return a 2-4 sentence caption string that can be used for social media

**What happens if it fails or returns nothing:**&lt;!-- What should the agent do if the outfit data is incomplete? --&gt; It should return (not raise) an error message string saying it can't generate a fit card without an outfit suggestion.

---

### Additional Tools (if any)

&lt;!-- Copy the block above for any tools beyond the required three --&gt;

---

## Planning Loop

**How does your agent decide which tool to call next?**&lt;!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? --&gt;

Single linear loop with one conditional branch.

1. Parse the query (regex) into description, size, max_price.
2. Run the search tool.
3. if results are empty → write an error to state and return early. The outfit and fit-card tools are skipped.
4. Otherwise hold the top result as the selected item.
5. Run the outfit tool against the selected item + wardrobe.
6. Run the fit-card tool against the outfit string + selected item.
7. Return state.

Behavior changes only at step 3 — that's the one place the agent decides to stop vs. keep going.

---

## State Management

**How does information from one tool get passed to the next?**&lt;!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? --&gt;

One session dict per run, created fresh at the start. Each step writes to one specific field; the next step reads from it. No globals.

- `query` → raw user input
- `parsed` → description, size, max_price (written by parsing step)
- `search_results` → list from search tool
- `selected_item` → `search_results[0]`, used by both outfit and fit-card tools
- `wardrobe` → passed in by caller, read by outfit tool
- `outfit_suggestion` → string from outfit tool
- `fit_card` → string from fit-card tool
- `error` → set only if the run ended early (otherwise `None`)

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
| --- | --- | --- |
| search_listings | No results match the query | Error message of "no items found, try different keyword" and returns early. Outfit and fit-card tools are skipped. |
| suggest_outfit | Wardrobe is empty | Tool falls back to general advice from the LLM which is not tied to specific wardrobe pieces. |
| create_fit_card | Outfit input is missing or incomplete | Returns a descriptive error string. Agent stores it in fit_card result and the UI shows it in panel. |

---

## Architecture

&lt;!-- Draw a diagram of your agent showing how the components connect: User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card) ↕ State / Session Show what triggers each tool, how state flows between them, and where error paths branch off. ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded sketch are all fine. You'll share this diagram with an AI tool when asking it to implement the planning loop and each individual tool. --&gt;

```
User query
    │
    ▼
Planning Loop ──────────────────────────────────────┐
    │                                               │
    ├─► Parse query (regex)                         │
    │       │  description, size, max_price         │
    │       ▼                                       │
    │   session["parsed"]                           │
    │       │                                       │
    ├─► search_listings                             │
    │       │ results == []                         │
    │       ├──► [ERROR] set session["error"] ──────┤
    │       │ results = [item, ...]                 │
    │       ▼                                       │
    │   session["selected_item"] = results[0]       │
    │       │                                       │
    ├─► suggest_outfit  (empty wardrobe → fallback) │
    │       │                                       │
    │   session["outfit_suggestion"]                │
    │       │                                       │
    └─► create_fit_card (empty outfit → err string) │
            │                                       │
            ▼                                       │
        session["fit_card"]                         │
            │                                       │
            ▼                                       │
        Return session  ◄───────────────────────────┘
                          (error path returns here)
```

---

## AI Tool Plan

&lt;!-- For each part of the implementation below, describe: - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.) - What you'll give it as input (which sections of this planning.md, your agent diagram) - What you expect it to produce - How you'll verify the output matches your spec before moving on

```
 "I'll use AI to help me code" is not a plan.
 "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
 search_listings() using load_listings() from the data loader — then test it against 3 queries
 before trusting it" is a plan. -->
```

**Milestone 3 — Individual tool implementations:** I will use Claude. For each tool I will paste in the tool's spec block ask claude to implement each tool before moving on to the next. I will verify the result matches the proper output I'm looking for. Then I will run the pytest tests until all tests pass before moving on.

**Milestone 4 — Planning loop and state management:** I will use Claude. I will paste in the planning loop section, state management, and archtecture diagram. I will then ask it to implement run_agent function. Then I will verify each step to make sure nothing is hardcoded and every step functions properly. I will also run the CLI test from [agent.py](http://agent.py) for the happy path and no results paths.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**&lt;!-- What does the agent do first? Which tool is called? With what input? --&gt; Agent parses the user query with basic string parsing to extract the inputs description="vintage graphic tee", size=None, max_price=30.0. It then calls search_listings(description, size, max_price) which filters and scores the mock listings to return a sorted list of matches.

**Step 2:**&lt;!-- What happens next? What was returned from step 1? What tool is called now? --&gt; Agent checks the output of step 1, search_results. If this list is empty, it return an error message that No thriftable items were found matching the query and to try different keywords. If the list is not empty the agent picks the first/top result in search_results and calls suggest_outfit(selected_item, wardrobe) where selected_item = search_results\[0\] and wardrobe is the mock wardrobe. This function returns a string which states how to style the new item with the existing items from the wardrobe.

**Step 3:**&lt;!-- Continue until the full interaction is complete --&gt; Agent calls create_fit_card(outfit, new_item) with outfit being the result of step 2 and new_item being the top result from step 1. This function returns a short caption.

**Final output to user:**&lt;!-- What does the user actually see at the end? --&gt; The UI populates the top listing which is the summary of selected_item which comes from step 1. The outfit idea which comes from step 2. The fit card which comes from the output of step 3.