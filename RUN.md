# How to run the smoke test

This is the actual hands-on comparison: same model (`gemini-3.1-pro-preview`), same Vertex ADC, same docs corpus, same Typst binary — just swap the agent layer (`google-adk` → `pi-coding-agent`) and see what falls out.

---

## 0. One-time setup (~2 min)

```bash
cd "$(dirname pi-typst-test)/pi-typst-test"   # this directory

# 0a. ADC for Vertex (skip if already done elsewhere)
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# 0b. Install pi globally + extension deps locally
scripts/install.sh

# 0c. Sanity check
gcloud auth application-default print-access-token | head -c 30 ; echo
typst --version
pi --version
```

If `gcloud config get-value project` returns your project, `scripts/env.sh` will pick it up automatically. Otherwise export it:

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1     # or wherever your Vertex quota is
```

---

## 1. Smoke test (non-interactive, ~3 min)

```bash
scripts/smoke.sh
```

This runs four `pi -p` (print mode) prompts and grep-checks the output. Each prompt targets one piece of the stack:

| # | Test | What it proves |
|---|------|----------------|
| 1 | List the four custom tools | Extension actually loaded |
| 2 | Compile `workspace/main.typ`, fix errors | `compile_typ` + agent compile loop work end-to-end |
| 3 | `search_docs(touying)` for metropolis boilerplate | Vertex Flash-Lite + corpus loader work |
| 4 | Suggest a font, must call `list_fonts` first | Anti-hallucination guidance is being followed |

Logs land in `logs/<timestamp>/`. Exit code = number of failures (0 = all green).

---

## 2. Interactive session (where the real comparison happens)

```bash
scripts/run.sh
```

That drops you into pi's TUI. The slash commands worth knowing:

- `/help` — full command list
- `/sessions` — list past sessions
- `/resume` — pick one to continue
- `/compact` — force context compaction
- `/tree` — show the branch tree of the current session
- `Ctrl+C Ctrl+C` — exit (single Ctrl+C interrupts the current request)

Below are six concrete prompts to throw at it. Run the **same prompts** through your existing `typst-agent` and watch where each one diverges. Time-to-first-token, number of tool calls, and number of failed compiles are the three metrics worth tracking.

### 2.1 Compile loop + small edit

```
Compile workspace/main.typ. If it errors, fix it. Then add a CeTZ diagram below the table showing a simple flowchart with three boxes ("ingest", "transform", "load") connected by arrows. Use compile_typ.
```

What to watch:
- Does it call `search_docs(query=..., package="cetz")` or hallucinate the API?
- How many compile cycles before it ships?
- Does the final PDF actually open?

### 2.2 Touying deck (this is where ADK usually goes off the rails)

```
Build a 3-slide Touying deck at workspace/deck.typ using the metropolis theme.
- Slide 1: title "Quarterly Review", subtitle "Q3 2025"
- Slide 2: a code block (use codly) showing a 5-line python snippet
- Slide 3: a CeTZ diagram with three boxes connected by arrows
Compile to PDF when done. Use search_docs for touying, codly, and cetz.
```

What to watch:
- Does it import `touying:0.7.3`, then `themes.metropolis: *`, then `#show: metropolis-theme.with(...)` — or does it invent something else?
- Does it call `search_docs` three times (once per package) or try to wing it?
- Does the deck actually have 3 slides?

### 2.3 Anti-hallucination — fonts

```
Set the body font of workspace/main.typ to a sans-serif that's actually installed on this machine. List your candidates first by calling list_fonts, pick one, then edit the file and recompile.
```

What to watch:
- Does it call `list_fonts` BEFORE editing?
- If `list_fonts` returns nothing matching its first guess, does it fall back, or push through and let typst silently substitute?

### 2.4 Bad request — should ask one clarifier

```
Make my deck better.
```

What to watch:
- Does it ask exactly one targeted question, or does it dive in and rewrite everything?
- The system prompt says "one question max, then ship on whatever you get back" — does that hold?

### 2.5 Compaction stress

In the same session, after the four prompts above, run:

```
/compact
```

Then:

```
What was the second slide of the deck supposed to contain? Answer in one line.
```

What to watch:
- Does compaction preserve enough state for it to remember? Pi's compaction is documented in `pi-mono-main/packages/coding-agent/docs/compaction.md`.

### 2.6 Session resume

Quit (`Ctrl+C` twice). Then:

```bash
pi -r --provider google-vertex --model gemini-3.1-pro-preview --extension ./extensions/typst-tools.ts
```

Pick the session you just had. Ask:

```
What's in workspace/ now?
```

It should remember and not re-list from scratch.

---

## 3. Side-by-side with your typst-agent

Run the same prompts through both agents and fill in this table:

| prompt | typst-agent (ADK) | pi-coding-agent | winner |
|--------|-------------------|-----------------|--------|
| 2.1 compile loop | tool calls / compiles / final PDF? | same | |
| 2.2 touying deck | tool calls / compiles / final PDF? | same | |
| 2.3 fonts | called list_fonts first? | same | |
| 2.4 vague brief | one clarifier or essay? | same | |
| 2.5 compaction | remembered slide 2? | same | |
| 2.6 resume | remembered workspace/? | same | |

If pi wins ≥ 4 of 6 with comparable response time, you have your answer about whether to keep ADK.

---

## 4. Adjusting the test

- **Different model** — `PI_MODEL=gemini-3.1-flash-preview scripts/run.sh` (or any id from pi-mono-main/packages/ai/src/models.generated.ts under provider `google-vertex`).
- **Different router model for search_docs** — `PI_TYPST_ROUTER_MODEL=gemini-2.5-flash-lite scripts/run.sh`.
- **Different region** — `GOOGLE_CLOUD_LOCATION=europe-west4 scripts/run.sh`.
- **Add more tools** — drop another `pi.registerTool(...)` block into `extensions/typst-tools.ts` and re-launch.
