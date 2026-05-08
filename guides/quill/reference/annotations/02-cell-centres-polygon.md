# Recipe: filled polygon between cell centres

Use *fractional* column / row indices to ask for the **centre** of a
cell. Then return a `polygon(...)` shape from the callback to draw
arbitrary geometry.

```typst
#quantum-circuit(
  1, $X$, 2, [\ ],
  1, 2, $Y$, [\ ],
  1, 1, $H$, meter(),
  annotate((1.5, 3.5, 2.5), (0.5, 1.5, 2.5), z: "above",
    ((x0, x1, x2), (y0, y1, y2)) => (
      content: polygon(
        (x0, y0), (x1, y1), (x2, y2),
        fill: rgb("#1020EE50"), stroke: .5pt + black
      ),
    ),
  )
)
```

- `1.5` → centre of column 1, `3.5` → centre of column 3, `2.5` →
  centre of column 2.
- Same convention on rows: `0.5` is the centre of row 0, etc.
- Returning `(content: polygon(...))` lets Quill expand its bounding
  box to fit the polygon.

See [`examples/02-cell-centres-polygon/02-cell-centres-polygon.typ`](examples/02-cell-centres-polygon/02-cell-centres-polygon.typ).

## Pitfalls

- `polygon((x0, y0), (x1, y1), (x2, y2))` accepts coordinate pairs as
  positional arguments — wrap each pair in parentheses.
- `z: "above"` puts the polygon on top of gates; without it the gates
  cover the polygon.
- For very transparent fills (`rgb("...50")` etc.), make sure the
  page background isn't the same colour or it will appear invisible.

## Related

- Reference: [`annotate`](../decorations/08-annotate.md)
- Tutorial: [tutorial 10](../../tutorial/10-annotations.md)
