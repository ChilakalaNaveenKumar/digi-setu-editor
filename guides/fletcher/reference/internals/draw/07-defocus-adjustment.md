# `defocus-adjustment(node, θ)`

For a long or wide node, return the adjusted anchor point that
prevents *all* edges from crowding into the geometric centre. Edges
arriving from the side hit the side; edges arriving from the top/bottom
spread out across the top/bottom edge.

The formula is documented at <https://www.desmos.com/calculator/irt0mvixky>.

## Signature

```typst
defocus-adjustment(node, θ) -> point
```

## Why this exists

Without defocus, three edges entering a long horizontal box from the
left would all meet at the box's exact centre, then visually splay
out from a single point — ugly. Defocus moves their intersection
points along the box's left edge instead.

## Where you control it

Public users tune the strength via `node(defocus: <number>, ...)`
(default 0.2). `defocus-adjustment` consumes that setting and returns
the actual anchor point.

## Example

A wide node fed by three arrows from different angles — the entry
points fan out across the side instead of all aiming at the centre.

See [`examples/07-defocus-adjustment/07-defocus-adjustment.typ`](examples/07-defocus-adjustment/07-defocus-adjustment.typ).

## Pitfalls

- For square / circular nodes the adjustment is zero — defocus is
  meaningful only when the node is asymmetric.
- Setting `defocus: 0` disables it; setting `defocus: 1` makes the
  effect very pronounced.

## Related

- [`get-node-anchor`](06-get-node-anchor.md) (calls defocus internally)
- [`find-farthest-intersection`](05-find-farthest-intersection.md)
