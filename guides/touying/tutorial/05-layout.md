# 05 — Page Layout

> Source: <https://touying-typ.github.io/docs/tutorials/layout>

## Basic concepts (Typst's page model)

Typst's page model is similar to the CSS box model: **margin**, **padding**,
**content**. Header and footer live *inside the margin*. Padding is added
manually with `#pad(...)` — there is no padding parameter on `set page`.

| Concept | Where it lives |
| ------- | -------------- |
| **Margin** | edges of the page; controlled by `set page(margin: ...)` |
| **Header** | content at top of the page (within the margin) |
| **Footer** | content at bottom (within the margin) |
| **`header-ascent`** | gap from the *outer* edge of the header container, percentage of `margin-top` |
| **`footer-descent`** | gap from the *outer* edge of the footer container |
| **`#place(...)`** | absolute positioning relative to parent without affecting flow |

## Page management — `config-page`

In Typst, `set page(...)` *creates* a new page rather than modifying the
current one. Touying instead maintains `self.page` as a member dict, and
exposes it through `config-page(...)`:

```typst
#show: default-theme.with(
  config-page(
    margin: (x: 4em, y: 2em),
    header: align(top)[Header],
    footer: align(bottom)[Footer],
    header-ascent: 0em,
    footer-descent: 0em,
  ),
)
```

Set `config-common(zero-margin-header: true)` to apply automatic negative
padding so the header / footer span the whole page width.

> **Warning.** Do **not** call `#set page(...)` yourself — Touying resets
> it for the next slide. Use `config-page(...)` instead.

## Page columnisation — `composer`

`#slide[...]` accepts a `composer` parameter. Default is
`cols.with(columns: auto, gutter: 1em)`:

```typst
#slide[
  First column.
][
  Second column.
]
```

To control widths:

```typst
#slide(composer: (1fr, auto))[
  Left fills, right is auto.
][
  Right column.
]
```

## Equalising column heights with `lazy-v`

`lazy-v(1fr)` is a **deferred** vertical spacer that is invisible during
height measurement. Wrap your multi-column layout in `lazy-layout` (which
`cols` enables by default), and `lazy-v` will push trailing content to the
bottom of each column once the measured max-height is applied.

### Using `cols` (recommended)

```typst
#cols[
  #block(fill: luma(220), inset: .5em, radius: .2em, width: 100%)[
    #lorem(10)
    #lazy-v(1fr)
    Bottom left.
  ]
][
  #block(fill: luma(220), inset: .5em, radius: .2em, width: 100%)[
    #lorem(20)
    #lazy-v(1fr)
    Bottom right.
  ]
]
```

Both columns end up the same height (matching the taller); "Bottom left."
and "Bottom right." align at the bottom. The overall block does **not**
expand to the full page — that is the whole point.

### Using a manual grid

```typst
#lazy-layout(grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  block(fill: luma(220), inset: .5em, radius: .2em, width: 100%)[
    #lorem(10)
    #lazy-v(1fr)
    Bottom left.
  ],
  block(fill: luma(220), inset: .5em, radius: .2em, width: 100%)[
    #lorem(20)
    #lazy-v(1fr)
    Bottom right.
  ],
))
```

> **Tip.** Pass `lazy-layout: false` to `cols` to opt out of the
> height-equalising behaviour.

## Preventing overflow — `breakable: false`

By default a slide that overflows continues onto the next page. To
disable this:

```typst
// Panic on overflow (the default once breakable: false is set)
#show: simple-theme.with(config-common(breakable: false))

// Visually clip overflow
#show: simple-theme.with(config-common(breakable: false, clip: true))

// Disable overflow detection (saves the extra layout pass)
#show: simple-theme.with(config-common(breakable: false, detect-overflow: false))
```

| Param | Default | Effect |
| ----- | ------- | ------ |
| `breakable` | `true` | When `false`, panic / clip on overflow. |
| `clip` | `false` | When `true` and `breakable: false`, content is visually truncated. |
| `detect-overflow` | `true` | When `true`, an extra layout pass calls `panic()` if content overflows. |

Both `clip` and `detect-overflow` only apply when `breakable: false`.

You can switch mid-presentation:

```typst
== Clipped Slide
#show: touying-set-config.with(config-common(clip: true))
#lorem(500)
```

## Example

See [`examples/05-layout/05-layout.typ`](./examples/05-layout/05-layout.typ).

## Pitfalls

- Never call `set page(...)`; use `config-page(...)`.
- `lazy-v` only works inside `cols` / `lazy-layout`; inside `#slide[...][...]`
  use `v(1fr)` instead (the slide composer already fills the page).
- `breakable: false` is most useful for agentic workflows where each slide
  must map cleanly to one PDF page.
