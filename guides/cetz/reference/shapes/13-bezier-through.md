# `bezier-through()` — Cubic Bezier Through Three Points

Draws a cubic bezier curve that passes through three given coordinates: the
start, an arbitrary pass-through, and the end.

## Signature

```text
bezier-through(
  start:        coordinate,
  pass-through: coordinate,
  end:          coordinate,
  name: none | str = none,
  ..style: style,
)
```

## Parameters

- **`start`** — start of the curve.
- **`pass-through`** — a point the curve must pass through.
- **`end`** — end of the curve.

## Styling

- **Root:** `bezier` (shared with [`bezier`](./12-bezier.md)).
- Supports `mark`.

## Anchors

Same as [`bezier`](./12-bezier.md): path anchors plus `ctrl-0`, `ctrl-1`. The
two control points are computed by CeTZ.

## Example

See [`examples/13-bezier-through/13-bezier-through.typ`](./examples/13-bezier-through/13-bezier-through.typ).

## Related

- [`bezier`](./12-bezier.md) — sibling shape (explicit control points)
- [`bezier.cubic-through-3points`](../internals/bezier/08-cubic-through-3points.md)
  — the math behind this shape
- [`bezier.quadratic-through-3points`](../internals/bezier/06-quadratic-through-3points.md)
  — the quadratic variant
