# `complex.div()` — Division

Divides two complex numbers — `V / W = V * inv(W)`.

## Signature

```text
div(V: complex, W: complex) -> complex
```

## Parameters

- **`V`** — numerator.
- **`W`** — denominator.

## Reference implementation

```typst
#let conj(V)   = (V.at(0), -V.at(1))
#let normsq(V) = V.at(0) * V.at(0) + V.at(1) * V.at(1)
#let mul(V, W) = (
  V.at(0) * W.at(0) - V.at(1) * W.at(1),
  V.at(1) * W.at(0) + V.at(0) * W.at(1),
)
#let inv(V)  = (conj(V).at(0) / normsq(V), conj(V).at(1) / normsq(V))
#let div(V, W) = mul(V, inv(W))
```

## Example

See [`examples/11-div/11-div.typ`](./examples/11-div/11-div.typ).
