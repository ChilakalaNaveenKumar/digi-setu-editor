# Touying — Slide / Presentation Package for Typst

> **Touying version:** 0.7.3
> **Source:** [touying-typ.github.io/docs](https://touying-typ.github.io/docs/intro)
> **Audience:** an LLM agent that authors `.typ` slide files using the
> [`touying`](https://typst.app/universe/package/touying) package. This
> sub-tree mirrors the upstream documentation site, organised the same way
> as the CeTZ / Fletcher / Quill packages under `../`.

[Touying](https://github.com/touying-typ/touying) ("touying", 投影 — *projection*
in Chinese) is a powerful slide / presentation package for Typst. It is
similar to LaTeX **Beamer** but benefits from Typst's modern syntax and
millisecond-fast compilation. Throughout the documentation, **slides** refers to
the whole slideshow, **slide** to a single page, and **subslide** to a sub-page
produced by an animation step (e.g. by `#pause`).

## Why Touying?

| vs. | Touying advantages |
| --- | ------------------ |
| **PowerPoint** | Content-and-style separation; themes handle visual design automatically. Excellent for code, math, theorems. |
| **Markdown slides** | Fine-grained typesetting (custom headers/footers, native math). `#pause` / `#meanwhile` for incremental reveals. |
| **LaTeX Beamer** | Compiles in **milliseconds** instead of seconds. Concise syntax, easy themes, plus `touying-reducer` for animated CeTZ / Fletcher diagrams. |
| **Polylux** | No `counter`/`locate` for `#pause` (no perf penalty). Richer theme utils, unified config API, easy theme switching. |

## Install / import

Touying lives on the Typst package registry — no manual install needed:

```typst
#import "@preview/touying:0.7.3": *
#import themes.simple: *
#show: simple-theme.with(aspect-ratio: "16-9")

= Title
== First Slide
Hello, Touying!
#pause
Hello, Typst!
```

The wildcard import is the **recommended** style — Touying re-exports
`themes`, `slide`, `pause`, `meanwhile`, `uncover`, `only`, `alternatives`,
`config-*`, `utils`, `components`, `pdfpc`, `magic`, etc. through one
namespace.

## Folder layout

| Folder | Contents |
| ------ | -------- |
| [`tutorial/`](./tutorial/) | Walk-through — getting started, code styles, sections, config, layout, multi-file, theme building, dynamic slides, progress, utilities. |
| [`themes/`](./themes/) | Built-in themes — `simple`, `metropolis`, `dewdrop`, `university`, `aqua`, `stargazer`, plus the `custom` recipe. |
| [`integration/`](./integration/) | Third-party package integrations — `pinit`, `mitex`, `cetz`, `fletcher`, `codly`, `theorion`. |
| [`external/`](./external/) | External tools — `touying-exporter`, `gistd`, `pympress`, `pdfpc`, `typst-preview` (Tinymist). |
| [`reference/core/`](./reference/core/) | Auto-generated API reference for the core modules — `configs`, `core`, `components`, `slides`, `utils`, `magic`, `pdfpc`. |
| [`reference/themes/`](./reference/themes/) | Auto-generated API reference per theme. |
| [`faq.md`](./faq.md) | Frequently-asked questions. |
| [`changelog.md`](./changelog.md) | Notable changes per version (0.7.x ↘ 0.4.x). |

## Reading order

1. [`tutorial/01-getting-started.md`](./tutorial/01-getting-started.md) — the
   first slide, then the more complex example with `university-theme` and
   integrated CeTZ / Fletcher animations.
2. [`tutorial/02-code-styles.md`](./tutorial/02-code-styles.md) — *simple* vs
   *block* style, `#slide[...]`, `#pagebreak`, `---`, "convention over
   configuration".
3. [`tutorial/03-sections.md`](./tutorial/03-sections.md) — sections,
   subsections, `slide-level`, the special `<touying:hidden>` heading
   labels, `#show: appendix`.
4. [`tutorial/04-settings.md`](./tutorial/04-settings.md) — `config-info`,
   `config-common(preamble: ...)`, `touying-set-config`, `touying-get-config`,
   frozen counters.
5. [`tutorial/05-layout.md`](./tutorial/05-layout.md) — page model, headers
   & footers, `composer`, multi-column, `lazy-v`, `breakable: false`.
6. [`tutorial/06-multi-file.md`](./tutorial/06-multi-file.md) — `globals.typ`
   / `main.typ` / `content.typ` split for large slide decks.
7. [`tutorial/dynamic/`](./tutorial/dynamic/) — `#pause`, `#meanwhile`, `only`,
   `uncover`, `alternatives`, math equation animation, cover function,
   handout mode, waypoints.
8. [`tutorial/progress/`](./tutorial/progress/) — slide counters,
   `last-slide-number`, progress bar, section utilities, progressive outlines.
9. [`tutorial/utilities/`](./tutorial/utilities/) — `fit-to-height`,
   `fit-to-width`.
10. [`tutorial/07-build-your-own-theme.md`](./tutorial/07-build-your-own-theme.md)
    — the full Bamboo-theme walk-through.
11. Pick a theme from [`themes/`](./themes/) and an integration as needed.

## Three things to remember

1. **One wildcard import is enough.** `#import "@preview/touying:0.7.3": *`
   then `#import themes.<name>: *` then `#show: <name>-theme.with(...)` —
   that's the whole shape.
2. **Don't call `set page(...)` yourself.** Touying owns the page args via
   `config-page(...)`. Calling `set page` directly is reset by the next slide.
3. **`#pause` is metadata-injected**, so it does **not** work inside `context
   { ... }` blocks, inside `raw`, or inside CeTZ / Fletcher canvases without
   `touying-reducer`. Use the callback-style `#slide(repeat: N, self => {...})`
   or wrap CeTZ / Fletcher with `touying-reducer.with(reduce: ..., cover: ...)`.

## How each reference page is structured

Every reference `.md` follows roughly the same shape (mirroring
`../cetz/reference/canvas/01-canvas.md`):

1. **Summary** — one paragraph.
2. **Signature** — fenced `text` block with positional + named args.
3. **Parameters** — bullets / table covering each arg.
4. **Pitfalls / cross-refs** — agent-targeted notes.
5. **Runnable example** — link to the sibling `.typ` file under
   `examples/<NN-name>/`.

`.typ` examples are kept short and **always wrap in the appropriate
theme call** so you can `typst compile` them as-is.

## Notes on fidelity

- All function signatures, parameter names, default values, slide function
  families, color theme dicts, and example snippets are taken verbatim
  from the upstream docs at <https://touying-typ.github.io/docs/>.
- Where the upstream example used `#import "@preview/touying:0.7.3": *`,
  the example file does the same so it compiles without extra imports.
- Cross-references to CeTZ, Fletcher, Pinit, MiTeX, Codly, Theorion are
  preserved.
- Compiled PDFs of every example live under
  `_out/touying/<section>/<NN-name>.pdf`, mirroring the source layout.
