# `draw-edge-arc(edge, debug)`

Render a **bent** (arc) edge. Fletcher uses this whenever
`edge(..., bend: <angle>)` is non-zero.

## Signature

```typst
draw-edge-arc(edge: dict, debug: int)
```

Important fields the helper reads from `edge`:

| Field | Effect |
| ----- | ------ |
| `vertices` | Start and end points (xy). |
| `bend` | Arc bend angle. The arc center is computed via [`get-arc-connecting-points`](../utils/03-get-arc-connecting-points.md). |
| `corner-radius` | (ignored — that's poly-line) |
| `marks`, `label`, `extrude`, `stroke` | Same semantics as line edges. |

## When you'd touch it

Implementing a custom curved edge that should still respect Fletcher's
mark + label conventions: build the `edge` dict yourself, then call
`draw-edge-arc`.

## Example

A bouquet of arcs from one node to several others — see
[`examples/03-draw-edge-arc/03-draw-edge-arc.typ`](examples/03-draw-edge-arc/03-draw-edge-arc.typ).

## Pitfalls

- Very small `bend:` (≤ 1deg) effectively degenerates to a straight
  line; Fletcher routes those through `draw-edge-line` instead.
- A `bend: 360deg` arc loops back to the start — useful for
  self-loops, but combine with `loop-angle:` rather than nudging
  manually.

## Related

- [`draw-edge-line`](02-draw-edge-line.md)
- [`get-arc-connecting-points`](../utils/03-get-arc-connecting-points.md)
- [Tutorial: edges](../../../tutorial/04-edges.md)
