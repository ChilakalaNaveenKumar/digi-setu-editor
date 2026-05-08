# 02 — Code Style

> Source: <https://touying-typ.github.io/docs/tutorials/code-styles>

Touying supports two writing styles: **simple style** (just write Typst) and
**block style** (`#slide[...]`). They can be mixed within the same file.

## Simple style

Type content under headings, just like a normal Typst document. Headings
delimit slides; `#pause` triggers an animation step.

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

A blank-titled slide is created with `== <touying:hidden>` (or any label
that suppresses the section/slide-title display — see
[`03-sections.md`](./03-sections.md)).

To force a new page **without** changing the title, use either `#pagebreak()`
or `---`. Touying parses `---` as `#pagebreak()`:

```typst
== First Slide
Hello, Touying!
---
Hello, Typst!
```

## Block style

For more powerful or clearer-structured slides, use `#slide[...]`:

```typst
= Title
== First Slide
#slide[
  Hello, Touying!
  #pause
  Hello, Typst!
]
```

`#empty-slide[]` makes a slide with no header / footer (useful for cover
images or full-bleed content).

Why prefer the block style?

1. Theme-specific slide functions (`#focus-slide[...]`, `#title-slide(...)`,
   `#matrix-slide[...]`, `#new-section-slide(...)`, `#centered-slide[...]`,
   `#outline-slide()`, …) only exist in block form.
2. Some themes give `#slide(...)` extra parameters (e.g. `metropolis-theme`'s
   `align: horizon`).
3. **Callback-style slides** — `#slide(repeat: N, self => {...})` — are the
   only way to use `only` / `uncover` / `alternatives` reliably across
   themes (see [`dynamic/02-complex.md`](./dynamic/02-complex.md)).
4. Easier to spot pagination boundaries in long files.

## Convention over configuration

When you use the simple theme, a level-1 heading auto-creates a *section*
slide. That happens because `simple-theme` registers
`config-common(slide-fn: slide, new-section-slide-fn: new-section-slide)`.

To suppress the auto-section slide:

```typst
#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-common(new-section-slide-fn: none),
)
```

To register a *custom* section slide:

```typst
#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-common(new-section-slide-fn: section => {
    touying-slide-wrapper(self => {
      touying-slide(
        self: self,
        {
          set align(center + horizon)
          set text(size: 2em, fill: self.colors.primary,
                   style: "italic", weight: "bold")
          utils.display-current-heading(level: 1)
        },
      )
    })
  }),
)
```

## Example

See [`examples/02-code-styles/02-code-styles.typ`](./examples/02-code-styles/02-code-styles.typ)
for a runnable file that shows both styles side-by-side.

## Pitfalls

- The auto-section-slide is **per-theme**. `simple`, `dewdrop`,
  `metropolis`, `university`, `aqua`, `stargazer` all register one;
  override with `config-common(new-section-slide-fn: none)` if you want
  bare headings.
- `#empty-slide[...]` is theme-defined too — not all themes export it.
- `---` only works at the top level. Inside a `#slide[...]` block use
  `#pagebreak(weak: true)` or split into two `#slide`s.
