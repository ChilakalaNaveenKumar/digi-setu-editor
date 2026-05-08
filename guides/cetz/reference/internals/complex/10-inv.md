# `complex.inv()` — Multiplicative Inverse

Inverts a complex number — `1 / V = conj(V) / |V|²`.

## Signature

```text
inv(V: complex) -> complex
```

## Parameters

- **`V`** — a complex number.

## Reference implementation

```typst
#let conj(V)   = (V.at(0), -V.at(1))
#let normsq(V) = V.at(0) * V.at(0) + V.at(1) * V.at(1)
#let inv(V)    = (conj(V).at(0) / normsq(V), conj(V).at(1) / normsq(V))
```

## Example

See [`examples/10-inv/10-inv.typ`](./examples/10-inv/10-inv.typ).
