# `polygon()` — Closed Polygons

`polygon` draws a closed shape from a list of vertices. Use the static
`polygon.regular(...)` for equal-sided polygons (triangle, hexagon, etc.).

## Signature

```text
polygon(
  fill:      none | color | gradient | tiling = none,
  fill-rule: "non-zero" | "even-odd" = "non-zero",
  stroke:    none | auto | length | color | gradient | stroke | tiling | dictionary = auto,
  ..vertices: array,    // (x, y) pairs; relative or absolute
) -> content

polygon.regular(
  fill:     none | color | gradient | tiling = none,
  stroke:   none | auto | length | color | gradient | stroke | tiling | dictionary = auto,
  size:     length = 1em,    // diameter of the circumcircle
  vertices: int = 3,
) -> content
```

The polygon is **closed automatically** — you don't need to repeat the
first point.

## Vertex coordinates

Vertices are `(x, y)` arrays where each component may be a length, a
ratio, or a `relative`. Coordinates are absolute within the polygon's
local frame; ratios are relative to the parent container.

## Fill rule

`"non-zero"` (default) treats overlapping subloops as merged. `"even-odd"`
treats every other crossing as "outside", which lets self-intersecting
polygons (stars) show holes:

```typst
#let star = polygon.with(
  (25pt, 0pt), (10pt, 50pt), (50pt, 20pt), (0pt, 20pt), (40pt, 50pt),
)
#star(fill: red, fill-rule: "non-zero")
#star(fill: red, fill-rule: "even-odd")
```

## When to use what

| Use case                              | Reach for                               |
| ------------------------------------- | --------------------------------------- |
| Custom convex/concave shape           | `polygon((x1, y1), (x2, y2), ...)`      |
| Triangle / hexagon / N-gon            | `polygon.regular(size: ..., vertices: N)` |
| Curves between vertices               | Use [`curve`](./03-curve.md) instead.   |
