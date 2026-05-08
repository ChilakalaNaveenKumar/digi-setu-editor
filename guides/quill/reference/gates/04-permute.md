# `permute()` — visualised qubit permutation

Draws a permutation of `n` consecutive qubits as crossing wires.
`permute(p_0, p_1, ..., p_{n-1})` maps qubit at position *k* to qubit
at position `p_k`. Indices are 0-based and refer to wires inside the
permutation block.

## Signature

```typst
permute(
  ..qubits:    int,
  width:       length = 30pt,
  bend:        ratio  = 100%,
  separation:  auto | none | length | color | stroke = auto,
  wire-count:  int | array = 1,
  stroke:      auto | stroke | array = auto,
  x, y,
)
```

## Variants

| Form | Effect |
| ---- | ------ |
| `permute(1, 0)` | Two-qubit swap (same as `swap`). |
| `permute(2, 0, 1)` | Cyclic permutation of 3 qubits. |
| `permute(2, 0, 1, bend: 0%)` | Straight crossing wires (no bezier bend). |
| `permute(1, 0, separation: red)` | Red separator under overlapping wires. |
| `permute(2, 0, 1, wire-count: (1, 2, 1))` | Mixed quantum / classical bundle. |

## Example

```typst
#quantum-circuit(
  wires: 3,
  1, permute(2, 0, 1), 1,
)

#quantum-circuit(
  wires: 3,
  1, permute(2, 0, 1, bend: 0%), 1,
)
```

See [`examples/04-permute/04-permute.typ`](examples/04-permute/04-permute.typ).

## Pitfalls

- `permute` only works on **consecutive** wires.
- Layout is heuristic: complex permutations (4+ qubits with multiple
  crossings) may overlap visually. Prefer `swap()` chains for
  predictable rendering.
- `permute` only renders quantum wires by default. Use `wire-count: ...`
  for classical / bundled cases.

## Related

- Two-qubit swap: [`swap`](08-swap.md)
- Wire bundles: [`nwire`](../decorations/04-nwire.md)
