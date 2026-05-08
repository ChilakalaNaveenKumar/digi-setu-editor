# `circle` — basic circle

Standard circle node shape. Picked automatically for square-ish
labels.

## Signature

```typst
circle(node, extrude)
```

## Example

```typst
#diagram(
  node-stroke: 1pt,
  node((0, 0), $A$, shape: circle),
  node((1, 0), [BIG],  shape: circle),
)
```

See [`examples/02-circle/02-circle.typ`](examples/02-circle/02-circle.typ).

## Pitfalls

- For wide labels, `circle` will be much wider than the label
  (radius = max(width, height) / 2). Use `ellipse` instead if you want
  the shape to "hug" the label aspect ratio.
