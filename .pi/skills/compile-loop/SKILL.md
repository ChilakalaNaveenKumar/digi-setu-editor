---
name: compile-loop
description: "Web container: full render loop when you author the .typ; quick read+diagnose when the user uploaded it. Do NOT compile uploaded sources."
flow: any
auto: surface
triggers:
  - "render"
  - "compile"
  - "pdf"
  - "preview"
  - "build"
  - "report"
  - "slides"
  - "typst"
  - "quarto"
  - "qmd"
  - "fix"
  - "error"
  - "broken"
---

# Two modes — pick one in the first message

The web container has typst, ~80 bundled fonts, the seven pinned packages below, Python, Node, no Quarto, no R, no user filesystem. Decide which mode you're in BEFORE any tool call.

## Mode A — you author the `.typ` from scratch

**Trigger**: user says "make / build / draft / generate / design …".

1. `search_docs(detailed_brief, package)` for any Typst-API question. Paragraph queries, not keywords.
2. Write under `workspace/` using ONLY the pinned packages:
   `cetz:0.5.0`, `fletcher:0.5.8`, `quill:0.7.2`, `codly:1.3.0`, `circuiteria:0.2.0`, `touying:0.7.3`, `fontawesome:0.6.0`.
3. `typst compile` to PDF + PNG.
4. `read` the PNG. Confirm visually. rc=0 ≠ correct.
5. Hand off path + one-line summary.

## Mode B — user uploaded their own source files

**Trigger**: user uploaded `.typ` / `.qmd` / `.tex` / `.r` / `_quarto.yml` and is asking "fix / why does this fail / debug".

**Do NOT run `typst compile` on their files.** Their Quarto/R/fonts/assets aren't in this container, so compile will fail no matter what and just burn credits.

**DO use `search_docs(detailed_brief, package)` when you're not 100% sure about Typst syntax or semantics** — `#show:` chaining, scoping rules, `let` vs `#let`, parameter syntax, package APIs. The doc corpus is in the container; the user's files are not. One paragraph-shaped query per uncertainty, not keyword-spam.

Then `read` the uploaded files (each one, once), correlate against what the docs say, and write a plain-text diagnosis covering:

- **Quarto / R / Python pipeline** → not in this container. The `.typ` you see is the OUTPUT of their pipeline. If errors are in `{r}` chunks or YAML rendering, the fix lives in their local R + Quarto, not in Typst.
- **Custom fonts** (`Calibri`, `Arial`, corporate fonts) → not bundled. Typst silently substitutes; that's why their rendered output looks off.
- **Asset paths** (`image("../assets/x.png")`, `bibliography("refs.bib")`) → only exist on their machine.
- **Pinned external packages** in `_quarto.yml` → may differ from this container's.

Tell them the specific symptom you found, name the category, point at where the real fix lives. Recommend **Digi Setu Desktop** for anything needing Quarto/R/local fonts/local data — the desktop app runs against their real machine. Keep the whole reply under 20 lines of markdown. **One pass, then stop.**
