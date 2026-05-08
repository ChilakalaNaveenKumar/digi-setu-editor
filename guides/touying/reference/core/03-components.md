# `components` — Reusable Layout Components

> Source: [src/components.typ](https://github.com/touying-typ/touying/blob/main/src/components.typ)

Reusable UI components used by the built-in themes and available to
custom themes.

## `cell(fill: ..., inset: ..., body)`

Convenience for full-width / full-height blocks:

```typst
#let cell = block.with(
  width: 100%,
  height: 100%,
  above: 0pt,
  below: 0pt,
  breakable: false,
)
```

Used by the metropolis / dewdrop / bamboo header backgrounds:

```typst
show: components.cell.with(fill: self.colors.primary, inset: 1em)
```

## `progress-bar(ratio, ...)`

Renders a horizontal progress bar using a ratio in `[0.0, 1.0]`:

```typst
#components.progress-bar(0.45, fill: blue, height: 4pt)
```

Combine with `utils.touying-progress` for a per-slide progress display.

## `progressive-outline(...)`

Outline that highlights the current section and grays out the rest.
Used by dewdrop, university, and other themes:

```typst
== Outline <touying:hidden>
#components.progressive-outline()
```

Common keys:

- `level` — heading level to display (default `auto`).
- `alpha` — transparency of inactive entries (default `40%`).
- `title` — outline title (`none` to hide).

## `custom-progressive-outline(...)`

Granular control over outline rendering — useful when the default
behavior doesn't fit:

```typst
#components.custom-progressive-outline(
  level: 1,
  show-past:    (true, false),
  show-future:  (true, false),
  show-current: (true, true, false),
  vspace:       (.5em, .0em),
  numbering:    ("1.1",),
  numbered:     (true, true),
  title:        none,
)
```

Each tuple-typed argument is indexed by heading level (index 0 = level 1).
Deeper levels inherit the last value.

## `adaptive-columns(body)`

Wraps `body` in a `columns(N, body)` where N is chosen so the content
fits one page. The canonical TOC pattern:

```typst
#components.adaptive-columns(outline(title: none, indent: 1em))
```

## `mini-slides(...)`

Mini-slides navigation strip used by the dewdrop theme:

```typst
#components.mini-slides(
  height: 2em,
  x: 2em,
  display-section: false,
  display-subsection: true,
  short-heading: true,
)
```

## `cols(columns: auto, gutter: 1em, ..bodies)`

Multi-column layout helper. Alias for `side-by-side` (added in v0.7.3).
Enables `lazy-layout` by default (so `lazy-v` works inside).

```typst
#cols[ Left ][ Right ]
#cols(columns: (1fr, 2fr))[ Left ][ Wider right ]
#cols(lazy-layout: false)[ Left ][ Right ]   // opt out of equal-height
```

## `side-by-side(...)`

Original name; same as `cols`. Pre-v0.7.3 themes still call this name.

## `lazy-v(amount)` / `lazy-h(amount)`

Deferred vertical / horizontal spacers — invisible during height
measurement but expand to push content when laid out at the measured
height. Use inside `cols` or `lazy-layout`:

```typst
#cols[
  #block[Content #lazy-v(1fr) Bottom-left]
][
  #block[More content #lazy-v(1fr) Bottom-right]
]
```

## `lazy-layout(body)`

Wraps `body` so that `lazy-v` / `lazy-h` markers trigger height
equalisation. `cols` enables this by default.

## `checkerboard(...)`

Renders a customisable checkerboard pattern (decorative). Customised
significantly in v0.6.2.

## See also

- [`../../tutorial/05-layout.md`](../../tutorial/05-layout.md) — page
  layout, `composer`, `lazy-v`.
- [`../../tutorial/progress/02-sections.md`](../../tutorial/progress/02-sections.md)
  — `progressive-outline` in context.
