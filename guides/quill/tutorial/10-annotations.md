# 10 — Annotations (`annotate`)

`annotate(...)` is Quill's escape hatch for arbitrary overlays. You ask
for the pixel coordinates of a few cells, then provide a callback that
draws anything (Typst content, shapes, labels) using those coordinates.

## Signature

```typst
annotate(
  columns: int | array,        // column indices to query
  rows:    int | array,        // row indices to query
  callback: (col-coords, row-coords) => content,
  z: "above" | "below"         // draw above or below the circuit
)
```

- The callback receives the **x-coordinates of the requested columns**
  and the **y-coordinates of the requested rows**, both as either a
  scalar (when you pass a single index) or an array (when you pass a
  list).
- Indices may be fractional. The integer part picks the cell; the
  fractional part is a **percentage of the cell width / height**, so
  `2.5` is the centre of the third column.
- The callback should return either a `content` value (drawn at
  `(0, 0)` of the circuit) **or** a dictionary with keys `content`,
  `dx`, `dy` so the circuit can size its bounding box correctly.

## Brace + label above two columns

```typst
#quantum-circuit(
  1, ctrl(1), $H$, meter(), [\ ],
  1, targ(), 1, meter(),
  annotate((2, 4), 0, ((x1, x2), y) => {
    let brace = math.lr($#block(height: x2 - x1)}$)
    place(dx: x1, dy: y, rotate(brace, -90deg, origin: top))
    let lab = [Readout circuit]
    context {
      let size = measure(lab)
      place(
        dx: x1 + (x2 - x1) / 2 - size.width / 2,
        dy: y - .6em - size.height,
        lab,
      )
    }
  })
)
```

What's happening:

- `(2, 4)` asks for x-coords of columns 2 and 4.
- `0` asks for the y-coord of row 0 (the first wire).
- The callback unpacks `((x1, x2), y)`, places a vertical brace and a
  centered label above the two columns.

## Filled polygon spanning three cells

```typst
#quantum-circuit(
  1, $X$, 2, [\ ],
  1, 2, $Y$, [\ ],
  1, 1, $H$, meter(),
  annotate((1.5, 3.5, 2.5), (0.5, 1.5, 2.5), z: "above",
    ((x0, x1, x2), (y0, y1, y2)) => {
    (
      content: polygon(
        (x0, y0), (x1, y1), (x2, y2),
        fill: rgb("#1020EE50"), stroke: .5pt + black
      ),
    )
  })
)
```

The `0.5` / `1.5` / `2.5` row/column values target *cell centres*. The
callback returns a dictionary with just `content:` — the polygon is
positioned by its own coordinates.

See [`examples/10-annotations/10-annotations.typ`](examples/10-annotations/10-annotations.typ).

## Pitfalls

- The circuit does **not** know the size of an annotation by default.
  Either return a content+`dx`+`dy` dictionary or set
  `circuit-padding` to leave room.
- `annotate(columns, rows, ...)` order matters — `columns` first.
- When the callback uses `place(...)`, return `none`-ish content; when
  it uses raw shapes (e.g. `polygon`) wrap them in `(content: ...)` so
  the bounding box adapts.

## Next

[`11-custom-gates.md`](11-custom-gates.md) — writing your own
`draw-function`.
