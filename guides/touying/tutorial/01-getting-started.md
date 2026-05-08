# 01 — Getting Started

> Source: <https://touying-typ.github.io/docs/start>

Touying ships through the Typst package registry. The Typst Web App and the
[Tinymist for VS Code](https://marketplace.visualstudio.com/items?itemName=myriad-dreamin.tinymist)
extension both download it automatically — there is no separate install step.

## The minimum viable deck

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

That is the entire shape:

1. `#import "@preview/touying:0.7.3": *` — wildcard-import the package.
2. `#import themes.simple: *` — wildcard-import a theme. Themes export their
   own `slide`, `title-slide`, `focus-slide`, `*-theme` functions.
3. `#show: simple-theme.with(aspect-ratio: "16-9")` — apply the theme as a
   show rule. Pass theme parameters and `config-*` calls here.
4. `=`, `==`, `===` — section / slide title / subsubsection (the heading
   level that creates a slide depends on `slide-level`, see
   [`03-sections.md`](./03-sections.md)).
5. `#pause` — split the current slide into subslides for incremental reveal.

> **Tip.** You can also use Typst's `#import "config.typ": *` and
> `#include "content.typ"` to implement a multi-file architecture (see
> [`06-multi-file.md`](./06-multi-file.md)).

## A more complete example

This is the canonical "tour" example from the upstream docs. It exercises
themes, animations, math, CeTZ / Fletcher / Theorion integration, multi-column
layout, and an appendix.

See [`examples/01-getting-started/01-getting-started.typ`](./examples/01-getting-started/01-getting-started.typ)
for the full source. The key ingredients:

```typst
#import "@preview/touying:0.7.3": *
#import themes.university: *
#import "@preview/cetz:0.5.0"
#import "@preview/fletcher:0.5.8" as fletcher: node, edge

// CeTZ + Fletcher Touying bindings
#let cetz-canvas = touying-reducer.with(
  reduce: cetz.canvas,
  cover: cetz.draw.hide.with(bounds: true),
)
#let fletcher-diagram = touying-reducer.with(
  reduce: fletcher.diagram,
  cover: fletcher.hide,
)

#show: university-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Title], subtitle: [Subtitle],
    author: [Authors], date: datetime.today(),
    institution: [Institution], contact: [contact\@mail.com],
    logo: emoji.school,
  ),
)
```

## What to read next

- [`02-code-styles.md`](./02-code-styles.md) — when to switch from simple
  `==`-style to `#slide[...]`.
- [`03-sections.md`](./03-sections.md) — controlling section / subsection
  semantics.
- [`themes/`](../themes/) — pick a theme that suits your aesthetic.

## Pitfalls

- `import themes.<name>: *` brings the theme's local `slide`,
  `title-slide`, `focus-slide`, etc. into scope. Without it,
  `#title-slide()` and `#focus-slide[...]` are undefined.
- The wildcard `*` import of `@preview/touying:0.7.3` is **recommended**.
  Touying's namespace is curated — `themes`, `slide`, `pause`,
  `meanwhile`, `only`, `uncover`, `alternatives`, `config-*`, `utils`,
  `components`, `pdfpc`, `magic`, `touying-reducer`, `touying-set-config`,
  `touying-get-config`, `touying-fn-wrapper`, `touying-equation`,
  `touying-mitex`, `touying-raw`, `appendix`, `waypoint`, etc.
- Without an `aspect-ratio:` argument the theme defaults are used (always
  `"16-9"` in the built-in themes).
