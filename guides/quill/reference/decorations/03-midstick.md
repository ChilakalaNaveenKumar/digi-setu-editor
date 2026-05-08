# `midstick()` — text on the wire (no box)

Plain text placed centred on the wire — like a gate body without a
box. Useful for ellipses (`…`), midpoint labels, or transparent
"gates" between two real ones.

## Signature

```typst
midstick(
  body:   content,
  n:      content = 1,
  label:  label-shape = none,
  fill:   none | color | gradient | tiling = none,
  x, y,
)
```

## Examples

```typst
// A calligraphic E on the wire.
#quantum-circuit(1, midstick($cal(E)$), 1)

// Multi-wire midstick (with a brace).
#quantum-circuit(
  1, midstick($cal(E)^2$, n: 2), 1, [\ ],
  1, 1
)

// An ellipsis spacer.
#quantum-circuit($H$, midstick($ dots $), $X$)
```

See [`examples/03-midstick/03-midstick.typ`](examples/03-midstick/03-midstick.typ).

## Pitfalls

- `midstick` does **not** break the wire — the wire passes through it.
  To break, drop a `phantom(...)` next to it or set a `fill:`.
- For a *boxed* gate body without text, use `gate(none, box: true)` —
  `midstick` is for unboxed text only.
- The default `fill: none` keeps the wire visible behind the body. Set
  `fill: white` (or the page colour) to "punch out" the wire under the
  text.

## Related

- Boxed gate: [`gate`](../gates/01-gate.md)
- Start / end labels: [`lstick`](01-lstick.md), [`rstick`](02-rstick.md)
