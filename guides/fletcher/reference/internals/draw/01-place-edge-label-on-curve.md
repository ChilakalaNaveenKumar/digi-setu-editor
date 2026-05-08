# `place-edge-label-on-curve(edge, curve, debug)`

Position a label along a *parametric* curve in xy space, honouring
all the edge's label options (`label-pos`, `label-side`, `label-sep`,
`label-anchor`, `label-angle`, `label-wrapper`).

## Signature

```typst
place-edge-label-on-curve(
  edge: dict,                  // must contain label-pos/-sep/-side/...
  curve: t: float -> point,    // parametric curve ℝ → ℝ²
  debug,
)
```

`curve(t)` should produce an xy-coordinate for `t` ∈ `[0, 1]`. The
helper picks `curve(edge.label-pos)`, computes the local tangent by
finite differences, and places the label perpendicular to it.

## When you need it

You wrote a custom edge shape (Bezier, spline, custom arc) and you
want the standard label-positioning logic to "just work".

## Example

A Bezier edge whose label is placed exactly at `t = 0.4`. See
[`examples/01-place-edge-label-on-curve/01-place-edge-label-on-curve.typ`](examples/01-place-edge-label-on-curve/01-place-edge-label-on-curve.typ).

## Pitfalls

- `curve(t)` must be smooth enough — the finite-difference tangent
  picks two samples close to `t` and breaks if they collide.
- Use `label-pos: 0.5` (a float) rather than `50%` if you want
  numerical control; both forms work.

## Related

- [Tutorial: edges (labels section)](../../../tutorial/04-edges.md)
- [`draw-edge-line`](02-draw-edge-line.md), [`draw-edge-arc`](03-draw-edge-arc.md)
