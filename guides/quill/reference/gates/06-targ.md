# `targ()` — CNOT target (`⊕`)

The target end of a controlled-X gate. Drawn as a circle with a cross
inside. Pair it with `ctrl(n)` on another wire to form a CNOT.

## Signature

```typst
targ(
  ..n:        int,
  fill:       none | auto | color | gradient | tiling = none,
  size:       length = 4.3pt,
  label,
  x, y,
  wire-count: int = 1,
  wire-stroke: auto | stroke = auto,
  wire-label: label-shape = none,
)
```

## Variants

| Form | Effect |
| ---- | ------ |
| `targ()` | Plain ⊕ on the current wire (no control wire). |
| `targ(2)` | ⊕ + control wire reaching up/down 2 wires. |
| `targ(fill: auto)` | Uses the circuit background fill (useful in dark mode). |
| `targ(size: 8pt)` | Larger target circle. |

The `..n` positional is the *relative wire offset* — same convention
as `ctrl(n)`. Pair `ctrl(1)` with `targ()` (no offset on the target
side) to form a top-down CNOT.

## Example: a CNOT

```typst
#quantum-circuit(
  1, ctrl(1), 1, [\ ],
  1, targ(),  1,
)
```

See [`examples/06-targ/06-targ.typ`](examples/06-targ/06-targ.typ).

## Pitfalls

- The control comes from `ctrl(...)`, not from `targ(...)` — `targ`
  alone is just the symbol.
- `fill: none` keeps the target transparent (the background bleeds
  through). For dark-mode circuits where the wire shows through the
  symbol, use `fill: auto`.
- `targ(2)` does **not** add a second target — it only changes which
  wire the (optional) control wire from `targ` reaches.

## Related

- The other half of CNOT: [`ctrl`](09-ctrl.md)
- Swap symbol: [`swap`](08-swap.md)
- Plain dot for CZ: [`ctrl()`](09-ctrl.md)
