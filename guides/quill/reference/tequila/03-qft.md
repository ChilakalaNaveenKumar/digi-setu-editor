# `tq.qft()` — Quantum Fourier Transform template

`tq.qft(n)` produces an `n`-qubit QFT subcircuit ready to spread into
a `quantum-circuit(..)`.

## Signature

```typst
qft(
  n: auto | int,
  x: int = 1,
  y: int = 0,
)
```

| Arg | Meaning |
| --- | ------- |
| `n` | Number of qubits in the QFT. |
| `x` | Column where the QFT starts. |
| `y` | Row where the QFT starts. |

## Example

```typst
#import "@preview/quill:0.7.2": tequila as tq

#quantum-circuit(
  ..tq.qft(2)
)
```

See [`examples/03-qft/03-qft.typ`](examples/03-qft/03-qft.typ).

## Pitfalls

- `tq.qft(2)` draws two qubits with one Hadamard, one controlled-`R_2`
  rotation, and a Hadamard. For 4+ qubits the controlled rotations
  multiply quickly; set a smaller `column-spacing` if it gets too wide.
- The function does **not** include the final swap step that some QFT
  definitions add; combine with `tq.swap(0, n - 1)` etc. to reverse
  qubit order if you need that variant.

## Related

- General assembly: [`01-build.md`](01-build.md)
- Composition: [`00-tequila-overview.md`](00-tequila-overview.md)
