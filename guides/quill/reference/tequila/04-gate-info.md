# Generic Tequila gates (`tq.gate`, `tq.mqgate`) and `gate-info`

The Quill manual documents an internal `gate-info(qubit, constructor, n,
supplements)` descriptor used by `tq.build(...)` to describe a single
operation. In Quill **0.7.2 this descriptor is internal** — it is not
re-exported on the public `tequila` module. The public surface is:

- `tq.gate(qubit, body, ...)` — generic single-qubit gate (qubit
  index *first*, body content second; styling kwargs match
  `gate(...)`).
- `tq.mqgate(start-qubit, body, n: ..., ...)` — generic multi-qubit
  gate.
- The named gate constructors `tq.h`, `tq.x`, `tq.cx`, ... wrap
  `tq.gate` / `tq.mqgate` for ergonomics.

Use these when one of the named gates doesn't fit (e.g. you want a
custom fill, draw-function, or label).

## Example: a tinted Hadamard via `tq.gate`

```typst
#import "@preview/quill:0.7.2": *
#import "@preview/quill:0.7.2": tequila as tq

#quantum-circuit(
  ..tq.build(
    tq.gate(0, $H$, fill: blue.lighten(70%)),
    tq.cx(0, 1),
  )
)
```

See [`examples/04-gate-info/04-gate-info.typ`](examples/04-gate-info/04-gate-info.typ).

## Pitfalls

- `tq.gate(qubit, body, ...)` takes the **qubit index first**, then
  the gate body. Reversing them errors with `cannot add content and
  integer`.
- `tq.gate-info(...)` is documented in the manual but **not** exposed
  on the `tequila` module in 0.7.2 — using it raises
  `module 'tequila' does not contain 'gate-info'`. Stick to the public
  `tq.gate` / `tq.mqgate` constructors.
- All Tequila gates are **dictionaries**, not content. They must be
  passed to `tq.build(...)` (and then spread with `..`) — passing them
  directly to `quantum-circuit(..)` will not work.

## Related

- Assembly: [`01-build.md`](01-build.md)
- Helpers: [`05-construct-two-qubit-gate.md`](05-construct-two-qubit-gate.md), [`06-construct-multi-controlled-gate.md`](06-construct-multi-controlled-gate.md)
