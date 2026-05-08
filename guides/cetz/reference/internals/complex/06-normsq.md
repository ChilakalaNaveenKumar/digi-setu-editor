# `complex.normsq()` — Squared Norm

Calculates the squared norm `|V|²` of a complex number — equivalent to
`re² + im²`.

## Signature

```text
normsq(V: complex) -> float
```

## Parameters

- **`V`** — a complex number.

## Reference implementation

```typst
#let normsq(V) = V.at(0) * V.at(0) + V.at(1) * V.at(1)
```

## Example

See [`examples/06-normsq/06-normsq.typ`](./examples/06-normsq/06-normsq.typ).
