# `annotate()` — custom overlay with cell coordinates

The escape hatch for arbitrary overlays. Quill calls your callback
with the *pixel coordinates* of the requested cells; you draw whatever
content (text, shapes, braces) using those coordinates.

## Signature

```typst
annotate(
  columns:  int | array,                            // column index or list
  rows:     int | array,                            // row index or list
  callback: (col-coords, row-coords) => content,    // what to draw
  z:        "below" | "above" = "below",
)
```

- `columns` / `rows` may be **fractional**: the integer part picks the
  cell, the fractional part is a percentage of the cell width / height.
  So `2.5` is the centre of the third column.
- The callback receives a scalar when you pass a single index, an
  array when you pass a list.
- The callback should return either a `content` value, or a
  dictionary with keys `content`, `dx`, `dy` so the circuit can
  enlarge its bounding box.

## Examples

### Simple overlay above a cell

```typst
#quantum-circuit(
  1, gate($H$), 1,
  annotate(1, 0, (x, y) => place(
    dx: x, dy: y - 1.2em,
    text(red, size: 8pt)[*Hadamard*],
  ))
)
```

### Brace + label across multiple columns

See [tutorial 10](../../tutorial/10-annotations.md) for the full
"readout circuit" example.

### Filled polygon across cell centres

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

See [`examples/08-annotate/08-annotate.typ`](examples/08-annotate/08-annotate.typ).

## Pitfalls

- The circuit cannot guess your annotation's size. To avoid clipping,
  return a `(content, dx, dy)` dictionary or set `circuit-padding` on
  the circuit.
- `columns` first, `rows` second — easy to swap.
- When the callback uses `place(...)`, return its result directly
  (Typst's `place` evaluates to content). When it builds raw shapes
  (`polygon`, `path`), wrap them in `(content: ...)` so the circuit
  knows the bounding box.

## Related

- Tutorial walkthrough: [tutorial 10](../../tutorial/10-annotations.md)
- Phase boundary: [`slice`](07-slice.md)
- Region overlay: [`gategroup`](06-gategroup.md)
