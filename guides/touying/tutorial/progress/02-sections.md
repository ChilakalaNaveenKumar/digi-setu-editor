# Progress 02 — Section Utilities

> Source: <https://touying-typ.github.io/docs/tutorials/progress/sections>

Touying injects invisible heading metadata into each slide, letting you
query the current section at any time via Typst's `query()` function.

## Displaying the current heading

`utils.display-current-heading(level: N)` returns the text of the most
recent level-N heading. Most themes use it for headers:

```typst
// Show the current section in the header
utils.display-current-heading(level: 1)

// Show the current subsection
utils.display-current-heading(level: 2)
```

`utils.display-current-short-heading(level: N)` strips numbering:

```typst
utils.display-current-short-heading(level: 2)
```

## Custom header with section name

```typst
#import "@preview/touying:0.7.3": *
#import themes.default: *

#show: default-theme.with(
  aspect-ratio: "16-9",
  config-page(
    header: [
      #text(gray, utils.display-current-heading(level: 2))
      #h(1fr)
      #context utils.slide-counter.display()
    ],
  ),
)

= My Section
== First Slide
Header shows "First Slide" on the right side.
== Second Slide
Header updates automatically.
```

## Progressive outlines

### Default — `components.progressive-outline()`

`components.progressive-outline()` renders an outline that highlights
the current section and grays out the rest — the look most themes use
for navigation:

```typst
#import themes.dewdrop: *
#show: dewdrop-theme.with(aspect-ratio: "16-9")

= Introduction
== Overview <touying:hidden>
#components.progressive-outline()

= Background
== Slide
Content.
```

`components.adaptive-columns(outline(...))` is a related variant that
splits a normal `outline()` into multiple columns to fit one page.

### Custom — `components.custom-progressive-outline()`

Full control over which entries show, when, and how:

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

The arrays follow the heading level — index 0 is level 1, etc. Anything
not specified for a deeper level inherits the last value.

### Section relationship helper

`utils.section-relationship(entry)` returns an int in
`(-2, -1, 0, 1, 2)`:

| Value | Meaning |
| ----- | ------- |
| `-2` | Earlier section, different top-level. |
| `-1` | Earlier sibling under the same top-level. |
| `0` | Current heading or its children. |
| `1` | Future sibling under the same top-level. |
| `2` | Later section, different top-level. |

Use it to roll your own outline styling:

```typst
#show outline.entry: it => {
  let r = utils.section-relationship(it)
  let cur = utils.current-heading()
  let alpha = if r == -2 or r > 0 { 40% } else { 100% }
  let weight = if r == 0 and cur.level == it.level { "bold" } else { "regular" }
  if it.level > 1 and calc.abs(r) > 1 {
    none
  } else {
    text(fill: utils.update-alpha(text.fill, alpha), weight: weight, it)
  }
}
```

## Example

See [`examples/02-sections/02-sections.typ`](./examples/02-sections/02-sections.typ).

## Pitfalls

- `utils.display-current-heading(level: 1)` returns *content*, not a
  string. To stringify, run it through `query()` and `it.body.text` (or
  use the helper `utils.display-current-short-heading`).
- `components.progressive-outline()` works best with a level-2 hidden
  outline placeholder (`== Outline <touying:hidden>`) so the outline
  itself doesn't appear in the outline.
- `utils.section-relationship` reads from the heading entry passed to
  the `outline.entry` show rule — call it from inside that show rule.
