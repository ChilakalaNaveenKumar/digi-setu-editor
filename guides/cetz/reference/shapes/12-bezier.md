# `bezier()` — Quadratic / Cubic Bezier Curve

Draws a quadratic (one control point) or cubic (two control points) bezier
curve between two endpoints.

## Signature

```text
bezier(
  start: coordinate,
  end:   coordinate,
  ..ctrl-style: coordinate | style,
  name:  none | str = none,
)
```

## Forms

| Call | Curve type |
| ---- | ---------- |
| `bezier(s, e, c)` | Quadratic — single control point. |
| `bezier(s, e, c1, c2)` | Cubic — two control points. |

## Styling

- **Root:** `bezier`
- Supports `mark` (start/end arrowheads).

## Anchors

Path anchors plus:

| Anchor | Position |
| ------ | -------- |
| `ctrl-0` | first control point |
| `ctrl-1` | second control point (cubic only) |

## Pitfalls

- The first **two** positional non-style arguments after `start`/`end` are
  treated as control points. Mixing in style values must use named-argument
  form, e.g. `bezier(s, e, c1, c2, stroke: red)`.
- For a curve fit through three points, use [`bezier-through`](./13-bezier-through.md).

## Example

See [`examples/12-bezier/12-bezier.typ`](./examples/12-bezier/12-bezier.typ).

## Related

- [`bezier-through`](./13-bezier-through.md) — Bezier fit through 3 points
- [`internals/bezier`](../internals/bezier/00-bezier-overview.md) — full
  Bezier math toolkit (`cubic-point`, `cubic-derivative`, `split`,
  `cubic-arclen`, `cubic-shorten`, `cubic-aabb`, …)
- [`intersection.line-cubic`](../internals/intersection/02-line-cubic.md) — line-cubic intersection
