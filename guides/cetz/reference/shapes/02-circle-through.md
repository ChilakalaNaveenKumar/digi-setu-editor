# `circle-through()` — Circle Through Three Points

Draws the unique circle that passes through three given points `a`, `b`, `c`.

## Signature

```text
circle-through(
  a: coordinate,
  b: coordinate,
  c: coordinate,
  name:   none | str = none,
  anchor: none | str = none,
  ..style: style,
)
```

## Parameters

- **`a`, `b`, `c`** — the three points the circle passes through. They must
  not be collinear.
- **`name`** / **`anchor`** — standard.
- **`..style`** — same style keys as [`circle`](./01-circle.md), except
  `radius` (which is computed from the three points).

## Styling

- **Root:** `circle` (shared with `circle()`).

## Anchors

Supports the same anchors as [`circle`](./01-circle.md), plus:

| Anchor | Position |
| ------ | -------- |
| `a` | input coordinate `a` |
| `b` | input coordinate `b` |
| `c` | input coordinate `c` |

## Pitfalls

- The three points must not lie on a straight line — otherwise the function
  panics.
- Internally calls [`cetz.util.calculate-circle-center-3pt`](../internals/util/09-calculate-circle-center-3pt.md);
  use that directly if you only need the centre.

## Example

See [`examples/02-circle-through/02-circle-through.typ`](./examples/02-circle-through/02-circle-through.typ).

## Related

- [`circle`](./01-circle.md) — sibling shape (centre + radius)
- [`util.calculate-circle-center-3pt`](../internals/util/09-calculate-circle-center-3pt.md)
  — the circumcentre math behind this shape
