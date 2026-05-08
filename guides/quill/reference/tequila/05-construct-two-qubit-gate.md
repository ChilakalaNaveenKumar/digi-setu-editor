# `construct-two-qubit-gate` — paired control-target

A small helper that produces a two-element instruction sequence: a
gate on a control qubit (or qubits) wired down/up to a target qubit
(or qubits) via Quill's relative-target mechanism.

## Manual signature

```typst
construct-two-qubit-gate(
  qubit1: int | array,
  qubit2: int | array,
  gate1:  function,
  gate2:  function,
)
```

| Arg | Meaning |
| --- | ------- |
| `qubit1` | Control qubit(s). |
| `qubit2` | Target qubit(s). |
| `gate1`  | Gate factory placed on the control qubit. Receives the relative target offset as its only positional argument. |
| `gate2`  | Gate factory placed on the target qubit. |

## Status in v0.7.2

The Quill 0.7.2 distribution does not currently re-export this helper
on the public `tequila` module. The public Tequila API achieves the
same effect with `tq.cx(control, target)` (control + CNOT target),
`tq.cz(c, t)` (control + control), and similar named constructors.

If you need the underlying wiring pattern manually, write it directly
with `ctrl(...)` / `targ(...)`:

```typst
#import "@preview/quill:0.7.2": *

#quantum-circuit(
  1, ctrl(1), 1, [\ ],
  1, targ(),  1,
)
```

See [`examples/05-construct-two-qubit-gate/05-construct-two-qubit-gate.typ`](examples/05-construct-two-qubit-gate/05-construct-two-qubit-gate.typ).

## When the manual API becomes available

If a future Quill version re-exports the helper, the calling pattern
will look like:

```typst
#tq.construct-two-qubit-gate(
  qubit1: 0,
  qubit2: 1,
  gate1:  ctrl,
  gate2:  targ,
)
```

`gate1` and `gate2` are bound *constructors* — `ctrl` (not `ctrl()`).

## Related

- Public CNOT helper: `tq.cx(control, target)` — see [`01-build.md`](01-build.md).
- Multi-control variant: [`06-construct-multi-controlled-gate.md`](06-construct-multi-controlled-gate.md).
