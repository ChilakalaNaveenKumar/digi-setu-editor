# `tq.graph-state()` — graph-state preparation circuit

`tq.graph-state(..edges, n: auto, x: 1, y: 0, invert: false)` builds
the canonical graph-state preparation circuit for the graph defined by
the edges (each edge is a two-tuple of qubit indices).

## Signature

```typst
graph-state(
  n:      auto | int = auto,
  x:      int = 1,
  y:      int = 0,
  invert: bool = false,
  ..edges: array,
)
```

| Arg | Meaning |
| --- | ------- |
| `n` | Number of qubits. `auto` picks `max(edge values) + 1`. |
| `x`, `y` | Placement of the subcircuit (column, row). |
| `invert` | Build the **uncompute** version (gates run in reverse). |
| `..edges` | One tuple per edge, e.g. `(1, 2), (2, 0)`. |

## Example

Three-qubit linear graph (edges `(1, 2)` and `(2, 0)`):

```typst
#import "@preview/quill:0.7.2": tequila as tq

#quantum-circuit(
  ..tq.graph-state((1, 2), (2, 0))
)
```

See [`examples/02-graph-state/02-graph-state.typ`](examples/02-graph-state/02-graph-state.typ).

## What it draws

For every qubit it inserts a Hadamard at the start, then for each
edge `(u, v)` it inserts a `cz` between qubit `u` and qubit `v`.
Setting `invert: true` reverses the order so it can be appended to
the end of a circuit to *uncompute* the graph state.

## Pitfalls

- Edge indices are 0-based; `n: auto` infers the wire count, but
  isolated qubits (without any edges) won't appear unless you set `n:`
  explicitly.
- Edges with the same endpoint draw multiple CZ stacks — visually
  they overlap; consider hand-laying for very dense graphs.

## Related

- General assembly: [`01-build.md`](01-build.md)
- Quantum Fourier Transform template: [`03-qft.md`](03-qft.md)
