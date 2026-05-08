# `get-arc-connecting-points(from, to, angle)`

Given two points and a *bend angle*, return the geometry of the arc
that connects them with that initial tangent angle.

## Signature

```typst
get-arc-connecting-points(
  from:  point,    // start (length, length)
  to:    point,    // end   (length, length)
  angle: angle,    // bend angle (chord ↔ tangent at `from`)
) -> dict
```

The returned dictionary contains:

| Key | Meaning |
| --- | ------- |
| `center` | Centre of the arc's circle. |
| `radius` | Arc radius. |
| `start`  | Start angle (CCW from `+x`). |
| `stop`   | End angle. |

The bend `0deg` degenerates into a straight line; `+45deg` curves the
arc to the *left* of the chord (as you walk from `from` to `to`),
and `-90deg` curves it sharply right.

## Example

```typst
let geom = fletcher.get-arc-connecting-points(
  (0pt, 0pt), (3cm, 0pt), 45deg,
)
fletcher.cetz.draw.arc(
  geom.center,
  start:  geom.start,
  stop:   geom.stop,
  radius: geom.radius,
  mark:   (end: ">"),
)
```

See [`examples/03-get-arc-connecting-points/03-get-arc-connecting-points.typ`](examples/03-get-arc-connecting-points/03-get-arc-connecting-points.typ).

## Pitfalls

- A `0deg` bend returns a degenerate arc (zero radius) — guard for
  this if you call the helper outside Fletcher's own machinery.
- For `±180deg` (a full half-turn) the chord and tangent are parallel
  but opposite; this is mathematically valid but visually unusual.

## Related

- [`draw-edge-arc`](../draw/03-draw-edge-arc.md) calls this internally.
- [Tutorial: edges](../../../tutorial/04-edges.md) for the `bend:` option.
