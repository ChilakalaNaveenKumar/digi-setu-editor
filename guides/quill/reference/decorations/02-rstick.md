# `rstick()` — label at the end of a wire

Mirror of `lstick`. Adds a label "sticking out" to the **right** of
the last cell on the current wire. With `n > 1` it spans wires and
shows a `}` brace by default.

## Signature

```typst
rstick(
  body:   content,
  n:      int = 1,
  brace:  auto | none | str = auto,
  pad:    length = 0pt,
  label:  label-shape = none,
  x, y,
)
```

## Brace defaults

Single wire (`n: 1`): no brace unless explicitly given.
Multi-wire (`n > 1`): default `}` brace.

## Examples

```typst
// Single-wire end label.
#quantum-circuit(1, rstick($|0〉$))

// Multi-wire end brace.
#quantum-circuit(
  1, rstick($rho$, n: 2), [\ ],
  1
)

// Square-bracket on the right.
#quantum-circuit(1, rstick($|psi〉$, brace: "]"))
```

See [`examples/02-rstick/02-rstick.typ`](examples/02-rstick/02-rstick.typ).

## Pitfalls

- `rstick` should be the **last** child on its wire — anything after it
  on the same row is laid out beyond the brace.
- A multi-wire `rstick(n: k)` reserves vertical space across `k`
  consecutive wires, so make sure those wires exist.
- If you want a tight brace next to the wire end, set `pad: 0pt`
  (default) — increase it for breathing room.

## Related

- Start-of-wire version: [`lstick`](01-lstick.md)
- Mid-text: [`midstick`](03-midstick.md)
