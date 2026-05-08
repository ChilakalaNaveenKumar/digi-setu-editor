# `circuit-padding` — outer bounding-box padding

`circuit-padding` is the **outer** padding of the circuit's bounding
box. Use it to leave room for `annotate(...)` overlays and labels that
extend beyond the gates themselves. It is *not* the gate-cell padding
(see `gate-padding`).

## Forms

| Form | Effect |
| ---- | ------ |
| `length` | Same padding on every side. |
| `dictionary` with keys `left`, `right`, `top`, `bottom` | Per-side. |

```typst
#quantum-circuit(
  circuit-padding: (top: 12pt, left: 4pt),
  1, gate($H$),
  annotate(1, 0, (x, y) => place(
    dx: x, dy: y - 10pt,
    text(red)[*top label!*],
  )),
)
```

See [`examples/06-circuit-padding/06-circuit-padding.typ`](examples/06-circuit-padding/06-circuit-padding.typ).

## Pitfalls

- Default is `0.4em` — already enough for sticks but **not** for tall
  annotations. Increase before adding overlays that extend upward /
  downward.
- A dictionary key not present falls back to `0pt`, **not** to a
  default. Use `length` for "same on all sides".

## Related

- Inside-the-box padding: `gate-padding` ([01-spacing.md](01-spacing.md))
- Annotations: [`annotate`](../decorations/08-annotate.md)
