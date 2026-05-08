# `arc-through()` — Arc Through Three Points

Draws an arc that passes through three coordinates `a`, `b`, `c`.

## Signature

```text
arc-through(
  a: coordinate,
  b: coordinate,
  c: coordinate,
  name: none | str = none,
  ..style: style,
)
```

## Parameters

- **`a`** — start of the arc.
- **`b`** — a point on the arc the curve must pass through.
- **`c`** — end of the arc.
- **`name`** / **`..style`** — standard.

## Styling

- **Root:** `arc` (shared with [`arc`](./03-arc.md)). All `arc` style keys
  apply, except `radius` which is computed.

## Anchors

Same anchors as [`arc`](./03-arc.md).

## Pitfalls

- The three points must not be collinear, otherwise the function panics.
- Like `arc`, `mode:` controls whether the implied chord/pie is closed.

## Example

See [`examples/04-arc-through/04-arc-through.typ`](./examples/04-arc-through/04-arc-through.typ).

## Related

- [`arc`](./03-arc.md) — sibling shape (centre + angle range)
- [`util.calculate-circle-center-3pt`](../internals/util/09-calculate-circle-center-3pt.md)
  — circumcentre math used to fit the arc
