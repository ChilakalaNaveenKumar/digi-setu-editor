# `ctrl()` — control dot

A filled (or open) control dot with a vertical wire to a relative
target. Pair it with `targ()`, `swap()`, `mqgate(...)`, or another
`ctrl()` (for CZ) to assemble multi-qubit gates.

## Signature

```typst
ctrl(
  ..n:        int,
  wire-count: int = 1,
  wire-stroke: auto | stroke = auto,
  open:       bool = false,
  fill,
  size:       length = 2.3pt,
  show-dot:   bool = true,
  wire-label: label-shape = none,
  label,
  x, y,
)
```

## Variants

| Form | Effect |
| ---- | ------ |
| `ctrl(1)` | Filled dot, control wire one row down. |
| `ctrl(-1)` | Filled dot, control wire one row up. |
| `ctrl()` | Filled dot **without** a control wire (use as the second end of a CZ). |
| `ctrl(1, open: true)` | Open (hollow) control dot. |
| `ctrl(1, show-dot: false)` | Plain vertical wire (no dot). |
| `ctrl(1, wire-count: 2)` | Classical control wire. |
| `ctrl(1, wire-label: $phi$)` | Wire annotated with label `φ`. |

## Examples

```typst
// Plain CNOT (top control, bottom target).
#quantum-circuit(
  1, ctrl(1), 1, [\ ],
  1, targ(),  1,
)

// CZ (two filled dots).
#quantum-circuit(
  1, ctrl(1), 1, [\ ],
  1, ctrl(),  1,
)

// Open control with classical wire.
#quantum-circuit(
  1, ctrl(1, open: true, wire-count: 2), 1, [\ ],
  setwire(2), 1, gate($M$), 1,
)
```

See [`examples/09-ctrl/09-ctrl.typ`](examples/09-ctrl/09-ctrl.typ).

## Pitfalls

- `ctrl()` (no offset) draws the dot but **no** wire — pair it with
  another `ctrl(n)` on a different row.
- `wire-count: 2` paints a *classical* control wire on the **control
  end**; the target wire's appearance is independent (use `setwire(2)`
  there if needed).
- `show-dot: false` only suppresses the dot — the vertical wire is
  still drawn. Combine with `targ()` to get a "blank" connector.

## Related

- CNOT target: [`targ`](06-targ.md)
- SWAP target: [`swap`](08-swap.md)
- Multi-qubit controlled gates: [`mqgate`](02-mqgate.md)
