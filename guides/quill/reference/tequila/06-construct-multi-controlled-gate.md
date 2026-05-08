# `construct-multi-controlled-gate` — multi-controlled gate

A helper that produces an N-control sequence: one or more `ctrl(...)`
items wired to a target gate.

## Manual signature

```typst
construct-multi-controlled-gate(
  controls: array,
  qubit:    int,
  gate:     function,
  ..args:   any,
)
```

| Arg | Meaning |
| --- | ------- |
| `controls` | Array of control qubit indices. |
| `qubit`    | Target qubit. |
| `gate`     | Bound gate factory placed at the target. |
| `..args`   | Additional kwargs forwarded to each `ctrl(...)`. |

## Status in v0.7.2

Like `construct-two-qubit-gate`, this helper is documented but **not**
re-exported in 0.7.2. The supported pattern is to compose the gates
yourself — Tequila's `tq.cx(controls, target)` accepts a tuple of
controls so two-control patterns can be one-liners; for three-control
Toffoli-style gates, write the layout by hand.

## Hand-laid Toffoli (CCX)

```typst
#import "@preview/quill:0.7.2": *

#quantum-circuit(
  1, ctrl(2), 1, [\ ],
  1, ctrl(1), 1, [\ ],
  1, targ(),  1,
)
```

See [`examples/06-construct-multi-controlled-gate/06-construct-multi-controlled-gate.typ`](examples/06-construct-multi-controlled-gate/06-construct-multi-controlled-gate.typ).

## Pitfalls

- **Both** ctrl's offsets must add up to land on the same target wire
  — easy to miscount when you have many controls.
- For five+ controls, consider drawing the controls with `ctrl(...)`
  but the target with `mqgate(target: ..., wire-count: 1, $X$)` so
  Quill can layout the wires consistently.

## Related

- Two-qubit version: [`05-construct-two-qubit-gate.md`](05-construct-two-qubit-gate.md)
- Direct multi-qubit gate: [`mqgate`](../gates/02-mqgate.md)
