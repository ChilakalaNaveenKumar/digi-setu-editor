# Recipe: vertical brace + label across two columns

The classic "Readout circuit" example from the Quill manual: a brace
spans the second-and-fourth columns of the top wire and a centred
text label sits above it.

```typst
#quantum-circuit(
  1, ctrl(1), $H$, meter(), [\ ],
  1, targ(),  1,    meter(),
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

Key ideas:

- `(2, 4)` asks for the x-coords of columns 2 and 4. The callback
  unpacks them as `(x1, x2)`.
- The brace is built with Typst's `math.lr` and a fixed-height block;
  rotating `-90deg` from `origin: top` makes it open to the right
  before the rotation, which becomes "open downward" after.
- `context { let size = measure(...) ... }` is needed because the
  label's measured size depends on the surrounding text style.

See [`examples/01-readout-brace/01-readout-brace.typ`](examples/01-readout-brace/01-readout-brace.typ).

## Pitfalls

- Without `context { measure(...) }` the label's width / height is
  inaccurate and the centering will drift across renders.
- The annotation is drawn `z: "below"` by default — call
  `annotate(..., z: "above", ...)` if it is hidden by gate boxes.
- The circuit's bounding box does **not** account for the label by
  default; either set `circuit-padding: (top: ...)` or return
  `(content, dx, dy)` from the callback so Quill can grow the box.

## Related

- Tutorial: [tutorial 10](../../tutorial/10-annotations.md)
- Reference: [`annotate`](../decorations/08-annotate.md)
