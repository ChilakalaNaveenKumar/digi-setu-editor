# `phase()` — phase gate (labelled point on the wire)

A small filled (or open) dot on the wire with a label nearby. The
default position of the label is `top + right`.

## Signature

```typst
phase(
  label:  content,
  open:   bool   = false,
  fill:   none | color | stroke = auto,
  size:   length = 2.3pt,
  x, y,
)
```

## Variants

| Form | Effect |
| ---- | ------ |
| `phase($alpha$)` | Filled dot with label `α`. |
| `phase($alpha$, open: true)` | Open (hollow) dot. |
| `phase($alpha$, fill: red)` | Red dot. |
| `phase($alpha$, size: 4pt)` | Bigger dot. |

## Example

```typst
#quantum-circuit(
  1, phase($alpha$), 1, phase($beta$, open: true), 1
)
```

See [`examples/07-phase/07-phase.typ`](examples/07-phase/07-phase.typ).

## Pitfalls

- `phase` does **not** stop the wire — it sits on top. To break the
  wire (e.g. for a fixed gap), insert a length item next to it.
- The default label position is `top + right`; for crowded layouts
  you'll often want `pos: top` or `pos: bottom + right` and a `dy`.

## Related

- Plain dot (no label): [`ctrl()`](09-ctrl.md)
- Boxed gate variant: [`gate(body, radius: 100%)`](01-gate.md)
