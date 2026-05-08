# `tq.build()` — assemble an instruction stream

`tq.build(..)` takes a sequence of Tequila instructions and returns a
collection of gates that can be **spread** into `quantum-circuit(..)`.

## Signature

```typst
build(
  n:           auto | int = auto,
  x:           int = 1,
  y:           int = 0,
  append-wire: bool = true,
  ..children:  any,
)
```

| Arg | Meaning |
| --- | ------- |
| `n` | Number of qubits. `auto` infers from the largest qubit index used. |
| `x` | Column where the subcircuit starts (1 = first column after lsticks). |
| `y` | Row where the subcircuit starts. |
| `append-wire` | If `true`, append a final column of outgoing wires. |
| `..children` | Tequila instructions in execution order. |

## Example

```typst
#import "@preview/quill:0.7.2": tequila as tq

#quantum-circuit(
  ..tq.build(
    tq.h(0),
    tq.cx(0, 1),
    tq.cx(0, 2),
    tq.measure(0, 3),
  ),
  [\ ], [\ ], [\ ], setwire(2)
)
```

See [`examples/01-build/01-build.typ`](examples/01-build/01-build.typ).

## Pitfalls

- The result of `tq.build(...)` must be **spread** with `..` — passing
  it as a single positional argument fails because `quantum-circuit`
  expects a flat list.
- `tq.measure(q_from, q_to)` puts a meter on `q_from` and the
  classical bit on `q_to` — make sure your circuit has enough wires
  (use `[\ ] [\ ]` row breaks plus `setwire(2)` if needed).
- `n: auto` only counts qubits used; if you want to draw an extra
  empty wire, set `n:` explicitly.

## Related

- Templates that internally use `tq.build`: [`02-graph-state.md`](02-graph-state.md), [`03-qft.md`](03-qft.md)
- Composition: see overview's *Composing templates* section.
