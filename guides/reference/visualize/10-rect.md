# `rect()` — Rectangles

`rect` is the workhorse boxed shape: any width × any height, optional
content, full styling vocabulary. The other boxed shapes (`circle`,
`ellipse`, `square`) reuse the same `fill`/`stroke`/`inset`/`outset`/
`radius` semantics defined here.

## Signature

```text
rect(
  width:  auto | relative = auto,
  height: auto | relative | fraction = auto,
  fill:   none | color | gradient | tiling = none,
  stroke: none | auto | length | color | gradient | stroke | tiling | dictionary = auto,
  radius: relative | dictionary = (:),
  inset:  relative | dictionary = 0% + 5pt,
  outset: relative | dictionary = (:),
  body:   none | content = none,
) -> content
```

## `stroke` accepts a per-side dictionary

```typst
#rect(stroke: (
  top:    2pt + red,
  bottom: 2pt + red,
  rest:   0.5pt + black,
))
```

Recognized keys (in precedence order): `top`, `right`, `bottom`, `left`,
`x` (= left & right), `y` (= top & bottom), `rest` (catch-all). Earlier
keys override later ones.

If you set a `fill`, the **default stroke disappears** (otherwise unfilled
rectangles render with a 1pt black border). Set both explicitly when you
need a filled, outlined rectangle.

## `radius` accepts a per-corner dictionary

```typst
#rect(radius: (
  top-left:    5pt,
  top-right:   20pt,
  bottom-right: 10pt,
  bottom-left:  0pt,
))
```

Shorthand keys `left`, `right`, `top`, `bottom` set two adjacent corners;
`rest` is the catch-all. Radii are clamped to `min(width, height) / 2`.

## `inset` vs `outset`

`inset` adds invisible padding **inside** the box (default `0% + 5pt` —
that's why text inside a `rect[...]` doesn't touch the border). `outset`
**enlarges** the box's painted area without changing the layout — useful
for highlight pills and stickers that should overlap surrounding elements
slightly.

Both accept a single value (`6pt`) or a per-side dictionary (`(x: 6pt,
y: 0pt)`).

## Sizing

- `auto` — sized to fit the body, falling back to a default if no body.
- A **relative length** (`50%`, `1cm`, `5cm + 2em`) — explicit size.
- `height: 1fr` — fills the remaining vertical space in a stack/page (only
  for `height`; `width` does not accept fractions).

## Common patterns

| Pattern                              | Snippet                                                      |
| ------------------------------------ | ------------------------------------------------------------ |
| Solid-color background bar           | `#rect(width: 100%, height: 4pt, fill: blue, stroke: none)`  |
| Outlined callout                     | `#rect(stroke: 1pt + black, inset: 8pt, [Callout text])`     |
| Tinted rounded card                  | `#rect(radius: 8pt, inset: 12pt, fill: aqua.lighten(70%), [...])` |
| Top-only border                      | `#rect(stroke: (top: 2pt + black, rest: none), inset: 8pt, [...])` |
