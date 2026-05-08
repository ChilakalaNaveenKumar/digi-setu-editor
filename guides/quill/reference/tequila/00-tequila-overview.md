# Tequila — overview

Tequila is a submodule of Quill that adds a **completely different way
of building circuits**, much closer to how Qiskit / OpenQASM works:
gates are issued sequentially against an implicit register, then
laid out automatically by packing them as tightly as possible.

## Import

```typst
#import "@preview/quill:0.7.2": tequila as tq
```

You then build a flat list of gate operations and spread them into
`quantum-circuit(..)` with the `..` operator:

```typst
#quantum-circuit(
  ..tq.build(
    tq.h(0),
    tq.cx(0, 1),
    tq.sdg(1),
  )
)
```

## Available gate constructors

`tq.x`, `tq.y`, `tq.z`, `tq.h`, `tq.s`, `tq.sdg`, `tq.sx`, `tq.sxdg`,
`tq.t`, `tq.tdg`, `tq.p`, `tq.rx`, `tq.ry`, `tq.rz`, `tq.u`, `tq.cx`,
`tq.cz`, `tq.swap`, `tq.measure`, `tq.barrier`, plus generic
`tq.gate` and `tq.mqgate`.

Qubit arguments accept **ranges and tuples** (Qiskit-style):

- `tq.h(range(5))` — Hadamard on the first 5 qubits.
- `tq.cx((0, 1), (1, 2))` — two CNOTs: q0→q1 and q1→q2.

## Pages in this folder

| Page | Function |
| ---- | -------- |
| [`01-build.md`](01-build.md) | `tq.build(...)` — assemble a flat instruction stream into circuit children. |
| [`02-graph-state.md`](02-graph-state.md) | `tq.graph-state(...)` template. |
| [`03-qft.md`](03-qft.md) | `tq.qft(n)` template. |
| [`04-gate-info.md`](04-gate-info.md) | `tq.gate-info(...)` low-level gate descriptor. |
| [`05-construct-two-qubit-gate.md`](05-construct-two-qubit-gate.md) | Helper for paired control-target patterns. |
| [`06-construct-multi-controlled-gate.md`](06-construct-multi-controlled-gate.md) | Helper for N-control gates. |

## Composing templates

`tq.build(...)` and `tq.graph-state(...)` both accept `x:` and `y:`
arguments so subcircuits can be placed at arbitrary positions of the
parent circuit. This makes Tequila the right choice for **assembling
multiple subcircuits**, while plain Quill is better for tightly hand-laid figures.

```typst
#quantum-circuit(
  ..tq.graph-state((0, 1), (1, 2)),
  ..tq.build(y: 3,
    tq.p($pi$, 0),
    tq.cx(0, (1, 2)),
  ),
  ..tq.graph-state(x: 6, y: 2, invert: true, (0, 1), (0, 2)),
)
```
