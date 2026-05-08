# `complex.ang()` — Signed Angle Between Two Complex Numbers

Returns the signed angle from `V` to `W` — equivalent to `arg(W / V)`.

## Signature

```text
ang(V: complex, W: complex) -> float
```

## Parameters

- **`V`** — start direction.
- **`W`** — end direction.

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
#let arg(V) = calc.atan2(..V) / 1rad
#let ang(V, W) = arg(div(W, V))
```

## Example

See [`examples/15-ang/15-ang.typ`](./examples/15-ang/15-ang.typ).
