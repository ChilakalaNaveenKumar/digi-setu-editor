# `draw-edge-line(edge, debug)`

Render a **straight** edge: stroke + marks + label. This is the
default renderer Fletcher uses for `edge((a, b), (c, d), "->")` with
no `bend:`.

## Signature

```typst
draw-edge-line(edge: dict, debug: int)
```

The `edge` dict must already contain everything `apply-edge-shift`
and friends produce — `vertices`, `extrude`, `stroke`, `marks`,
`label`, `label-side`, `label-pos`, `label-sep`, `label-anchor`.

## Example — manually invoking `draw-edge-line`

You'd normally never call this — Fletcher does. But if you wanted to
override what gets drawn:

```typst
render: (grid, nodes, edges, options) => fletcher.cetz.canvas({
  for e in edges {
    if e.kind == "line" { fletcher.draw-edge-line(e, options.debug) }
  }
})
```

See [`examples/02-draw-edge-line/02-draw-edge-line.typ`](examples/02-draw-edge-line/02-draw-edge-line.typ).

## Pitfalls

- `extrude:` produces *parallel* strokes — useful for tape-style or
  double-line arrows.
- `debug: 1+` overlays the stroke endpoints in red; very handy when
  marks look offset.

## Related

- [`draw-edge-arc`](03-draw-edge-arc.md), [`draw-edge-polyline`](04-draw-edge-polyline.md)
- [`place-edge-label-on-curve`](01-place-edge-label-on-curve.md)
