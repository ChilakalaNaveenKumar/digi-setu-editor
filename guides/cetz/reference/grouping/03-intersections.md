# `intersections()` — Compute Intersection Anchors

Calculates intersections between every pair of paths in the body and creates
one numbered anchor per intersection point. The resulting anchors are named
`<name>.0`, `<name>.1`, …, `<name>.n`.

## Signature

```text
intersections(
  name: str,
  ..elements: elements | str,
  samples:        int = 10,
  sort:           none | function = none,
  ignore-marks:   bool = false,
)
```

## Parameters

- **`name`** — prefix for the generated anchors.
  Note: this is *not* an element name like elsewhere — it's the anchor
  prefix.
- **`..elements`** — elements (drawn as part of the call) and/or names of
  elements (referenced but **not** drawn by `intersections`).
- **`samples`** — number of samples for non-linear segments. More samples =
  better precision, slower.
- **`sort`** — `(context, array<vector>) -> array<vector>`. CeTZ provides:
  - `cetz.sorting.points-by-distance(points, reference: (0, 0, 0))`
  - `cetz.sorting.points-by-angle(points, reference: (0, 0, 0))`
- **`ignore-marks`** — when `true`, mark shapes are ignored.

## Pitfalls

- You can use **hidden** elements ([`hide`](./01-hide.md)) inside the body
  to compute intersections with construction lines that aren't drawn.
- Anchors are zero-indexed; iterate them with
  [`for-each-anchor`](./10-for-each-anchor.md).

## Example

See [`examples/03-intersections/03-intersections.typ`](./examples/03-intersections/03-intersections.typ).

## Related

- [`internals/intersection`](../internals/intersection/00-intersection-overview.md)
  — the math behind this shape:
  [`line-line`](../internals/intersection/01-line-line.md),
  [`line-cubic`](../internals/intersection/02-line-cubic.md),
  [`line-path`](../internals/intersection/03-line-path.md),
  [`path-path`](../internals/intersection/04-path-path.md)
- [`util.sort-points-by-distance`](../internals/util/19-sort-points-by-distance.md)
  — what powers the optional `sort:` callback
