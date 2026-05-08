# `complex.dot()` — Complex Dot Product

Calculates the dot product of two complex numbers in R² —
`Re(V * conj(W))`.

## Signature

```text
dot(V: complex, W: complex) -> float
```

## Parameters

- **`V`**, **`W`** — complex operands.

## Reference implementation

```typst
#let conj(V) = (V.at(0), -V.at(1))
#let mul(V, W) = (
  V.at(0) * W.at(0) - V.at(1) * W.at(1),
  V.at(1) * W.at(0) + V.at(0) * W.at(1),
)
#let dot(V, W) = mul(V, conj(W)).at(0)
```

## Example

See [`examples/05-dot/05-dot.typ`](./examples/05-dot/05-dot.typ).
