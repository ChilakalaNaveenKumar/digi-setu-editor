# Recipe: hand-drawn arrow pointing at a gate

You can draw any Typst content from the `annotate` callback — Typst's
own `line(..., end: "->")` works perfectly for arrow annotations.

```typst
#quantum-circuit(
  circuit-padding: (top: 18pt, default: 4pt),
  1, gate($H$), ctrl(1), 1, [\ ],
  1, 1, targ(), 1,
  annotate(2, 0, (x, y) => {
    let target = (x, y - 4pt)
    let label-pos = (x + 18pt, y - 16pt)
    place(
      dx: 0pt, dy: 0pt,
      line(start: label-pos, end: target,
        stroke: 0.5pt + red,
        end: ()),  // empty caps
    )
    place(
      dx: label-pos.at(0), dy: label-pos.at(1) - 8pt,
      text(red, size: 8pt)[*This is the magic gate*],
    )
  })
)
```

See [`examples/03-arrow-overlay/03-arrow-overlay.typ`](examples/03-arrow-overlay/03-arrow-overlay.typ).

## Pitfalls

- Arrow heads on `line(...)` are tricky in Typst 0.14 — the safest
  pattern is to draw a short segment with `path(...)` or use a CeTZ
  canvas inside the `annotate` callback for richer shapes.
- The arrow's coordinates are **relative to the circuit's origin**,
  the same as cell coordinates returned by `annotate`.
- Set `circuit-padding` so the arrow's start point isn't clipped by
  the bounding box.

## Related

- For richer shapes use CeTZ inside `annotate(...)` — see
  [`guides/cetz/00-cetz-overview.md`](../../../cetz/00-cetz-overview.md).
- Reference: [`annotate`](../decorations/08-annotate.md)
