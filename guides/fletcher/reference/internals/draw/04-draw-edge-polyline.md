# `draw-edge-polyline(edge, debug)`

Render a **multi-segment** edge — what Fletcher uses for
`edge((a,b), v1, v2, …, (c,d))` and for relative-shorthand routes
like `edge((0, 0), "r,d,r", (3, 1))`.

## Signature

```typst
draw-edge-polyline(edge: dict, debug: int)
```

Reads from `edge`:

| Field | Effect |
| ----- | ------ |
| `vertices` | Two **or more** points (xy) — the polyline traces them in order. |
| `corner-radius` | Round each interior corner with this radius. |
| `marks`, `label`, `extrude`, `stroke` | Same as line edges. |

## When you'd touch it

You're routing edges around obstacles or building an L / Z shaped
connector and want corner rounding handled.

## Example — a Z-shape connector

```typst
edge((0, 0), "r,d,r", (3, 1), corner-radius: 4pt, "->")
```

See [`examples/04-draw-edge-polyline/04-draw-edge-polyline.typ`](examples/04-draw-edge-polyline/04-draw-edge-polyline.typ).

## Pitfalls

- `corner-radius:` larger than half the shortest segment will produce
  visible artefacts (the rounded corner overlaps the adjacent
  segment).
- Mixing relative shorthands and explicit coords on the same edge is
  legal, but each relative step is taken from the *previous* vertex.

## Related

- [`draw-edge-line`](02-draw-edge-line.md), [`draw-edge-arc`](03-draw-edge-arc.md)
- [Tutorial: edges](../../../tutorial/04-edges.md)
